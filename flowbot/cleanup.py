import os
import glob
import datetime
import shutil

def cleanup():
    root_path = '/home/ec2-user/luigi/flowbot/runtime-data/'
    print('switching to root path: ' + root_path)

    os.chdir(root_path)
    all_files = glob.glob(os.path.join(root_path, "*"))
    cur_time = datetime.datetime.now()
    for file in all_files:
        modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file))
        elapsed = cur_time - modified_time
        if elapsed > datetime.timedelta(days=3):
            print('Removing ' + file + ' --- Not modified for ' + str(elapsed))
            try:
                # try removing individual file
                os.remove(file)
            except Exception as e:
                # if that didn't work, try removing a directory path
                shutil.rmtree(file)
