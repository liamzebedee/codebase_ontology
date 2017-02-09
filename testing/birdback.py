import view
import model

import time
import os
import os.path
import sys
import shelve
import getpass
import subprocess
import glob
import shutil
import errno
import logging

import pyinotify
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib
import scandir

# This is so pyinotify can work in another background thread
GObject.threads_init()

class Controller(object):
	def __init__(self):
		self.backup_mediums = {}
		self.pidfile = os.path.expanduser("~/.birdback.pid")
		
		# Check that birdback isn't already running
		# -------------------deleteOldFiles----------------------
		pid = os.getpid()
		
		running = False # Innocent...
		if os.path.isfile(self.pidfile):
			try:
				oldpid = int(open(self.pidfile).readline().rstrip())
				try:
					os.kill(oldpid, 0)
					running = True # ...until proven guilty
				except OSError as err:
					if err.errno == os.errno.ESRCH:
						# OSError: [Errno 3] No such process
						print("stale pidfile, old pid: ", oldpid)
			except ValueError:
				# Corrupt pidfile, empty or not an int on first line
				pass
		if running:
			print("birdback is already running, exiting")
			sys.exit()
		else:
			open(self.pidfile, 'w').write("%d\n" % pid)
			print("pidfile updated")
		
		# Load preferences from disk
		# --------------------------
		preferences_path = os.path.join(GLib.get_user_config_dir(), 'birdback')
		self.preferences = model.Preferences(preferences_path)
		print("Preferences loaded from " + preferences_path)
		
		# Instantiate file system watchers
		# --------------------------------
		watch_manager = pyinotify.WatchManager()
		
		class BackupMediaDetector(pyinotify.ProcessEvent):
			def __init__(self, controller):
				self.controller = controller
			
			def process_IN_CREATE(self, event):
				path = event.pathname
				if path.startswith('/dev/disk/by-id/usb'):
					# Try to automatically mount it
					device_path = os.path.realpath("/dev/disk/by-id/"+os.readlink(path))
					try:
						# We use udisksctl here because it mounts to /media/USERNAME/XXX instead of simply /media/XXX
						subprocess.check_output(['udisksctl', 'mount', '--block-device', device_path])
					except:
						print('Error while mounting path: '+path)
					return
				else:
					print('HDD/USB inserted at: ' + path)
					if path not in self.controller.backup_mediums:
						self.controller.backup_mediums[path] = model.BackupMedium(path)
					self.controller.view.drive_inserted(self.controller.backup_mediums[path])

			def process_IN_DELETE(self, event):
				path = event.pathname
				print('HDD/USB removed at: ' + path)
				if path in self.controller.backup_mediums:
					self.controller.view.drive_removed(self.controller.backup_mediums[path])
					del self.controller.backup_mediums[path]
		
		self.backup_media_watcher = pyinotify.ThreadedNotifier(watch_manager, BackupMediaDetector(self))
		self.backup_media_watcher.start()
		
		watch_manager.add_watch(os.path.join('/media', getpass.getuser()), pyinotify.IN_DELETE | pyinotify.IN_CREATE, rec=False)
		watch_manager.add_watch('/dev/disk/by-id/', pyinotify.IN_CREATE, rec=False)
		print("Added watch for USB/HDDs")
	
	def run(self):		
		# Instantiate the view
		# --------------------
		self.view = view.View(self)
		print("View instantiated")
		
		# Detect existing HDDs/USBs
		# -------------------------
		os.chdir("/dev/disk/by-id")
		try:
			for path in glob.glob("usb*"):
				# Try to automatically mount it
				device_path = os.path.realpath("/dev/disk/by-id/"+os.readlink(path))
				mounts = open("/proc/mounts")
				for line in mounts:
					parts = line.split(' ')
					if parts[0] == device_path and parts[1].startswith(os.path.join('/media', getpass.getuser())):
						path = parts[1]
						self.backup_mediums[path] = model.BackupMedium(path)
						self.view.drive_inserted(self.backup_mediums[path])
				mounts.close()
		except Exception as exception:
			print('Error while detecting existing HDDs/USBs {0}: {1}'.format(path, exception))
	
		# Start main loop
		# ---------------
		print("Running main loop")
		Gtk.main()
	
	def signal_exit(self, _0, _1):
		self.quit()
	
	def quit(self, code=0):
		print("Quitting...")
		try:
			self.backup_media_watcher.stop()
			Gtk.main_quit()
			self.preferences.close()
		except Exception as e:
			print("Exception while quitting:")
			print(e)
		
		# DO NOT CHANGE THE ORDER OF CALLS BELOW
		try:
			os.remove(self.pidfile)
		except OSError:
			pass
	
	def backup(self, backup_medium, progress_callback):
		files_to_backup = []
				
		progress_callback("1/3 deleting old files from backup")
		self.delete_old_files(backup_medium, progress_callback)
		
		progress_callback("2/3 scanning changed documents")
		files_to_backup.extend(self.get_home_files_to_backup(backup_medium))
				
		progress_callback("3/3 backing up")
		for i, src_file in enumerate(files_to_backup):
			if not os.path.exists(backup_medium.path):
				raise Exception("Backup medium was removed")
			
			try:
				dest_dir = os.path.join(backup_medium.path, os.path.dirname(src_file[1:]))
				os.makedirs(dest_dir, exist_ok=True)
				shutil.copy2(src_file, dest_dir, follow_symlinks=False)
				
				progress = float(i / len(files_to_backup))
				progress_callback("3/3 backing up ({0:.1f}%)".format(100*progress))
			except OSError as e:
				if e.errno == errno.ENXIO:
					print("[Error] ENXIO for "+srcFile)
					continue
			except Exception as exception:
				if not os.path.exists(backup_medium.path):
					raise Exception("Backup device was removed")
				elif not os.path.exists(srcFile):
					print("[{0}]: not backing up because file doesn't exist - {1}".format(backup_medium.name, srcFile))
					continue
				else:
					# Something else failed like:
					#  - backup medium has no space left
					#  - we couldn't create the directory on the backup medium
					#  - we couldn't copy the file over
					raise exception
		
		progress_callback("backup complete")
		
	
	def get_home_files_to_backup(self, backup_medium):
		BACKUP_PATH = os.path.expanduser("~")
		EXCLUDES = [
			'.cache',
			'.ccache',
			'Downloads',
			'tmp',
			'.local/share/Trash'
		]
		
		excludes_by_user = []
		# The user-defined excludes are absolute file paths, so we must trim off the prefix
		for path in self.preferences.excluded_files:
			relpath = os.path.relpath(path, BACKUP_PATH)
			if relpath != '':
				excludes_by_user.append(relpath)
		
		filesToBackup = []
		
		for dirpath, dirs, files in scandir.walk(BACKUP_PATH, topdown=True):
			if not os.path.exists(backup_medium.path):
				raise Exception("Backup medium was removed")
            
            # Excludes
			dirs[:] = [directory for directory in dirs if directory not in EXCLUDES]
			dirs[:] = [directory for directory in dirs if directory not in excludes_by_user]
			
			# If we haven't backed up this file before
			if not os.path.exists(os.path.join(backup_medium.path, dirpath[1:])):
				for f in files:
					filesToBackup.append(os.path.join(dirpath, f))
			# If we have backed it up before, check if its different or not
			else:
				for f in files:
					absolute_file_path = os.path.join(dirpath, f)
					remoteMtime = -1
					try: 
						remoteMtime = os.path.getmtime(os.path.join(backup_medium.path, absolute_file_path[1:]))
					except:
						pass
					try:
						if os.path.getmtime(absolute_file_path) > remoteMtime:
							filesToBackup.append(absolute_file_path)
					except OSError as e:
						pass
			
		return filesToBackup
	
	def delete_old_files(self, backup_medium, progress_callback):		
		PATH = os.path.expanduser("~")
		for dirpath, dirs, files in scandir.walk(os.path.join(backup_medium.path, PATH[1:]), topdown=True):
			if not os.path.exists(backup_medium.path):
				raise Exception("Backup medium was removed")
			for d in dirs:
				absolute_file_path = os.path.join(dirpath, d)
				if not os.path.exists('/'+os.path.relpath(absolute_file_path,backup_medium.path)):
					try:
						shutil.rmtree(absolute_file_path)
					except:
						pass
			
			for f in files:
				absolute_file_path = os.path.join(dirpath, f)
				
				if not os.path.exists('/'+os.path.relpath(absolute_file_path, backup_medium.path)):
					try:
						os.remove(absolute_file_path)
					except:
						pass

