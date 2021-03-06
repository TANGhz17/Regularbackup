# coding: utf8
import os
import re
import shutil
import time
from threading import Lock
from utils.rtext import *
from datetime import date
import json

# from bypy import ByPy

# rb本体设置
SizeDisplay = True
SlotCount = 2
Prefix = '!!rb'
BackupPath = './rb_temp'
serverName = ""  # 压缩文件的名称前半段，后半段是时间
enable_compression = True # 是否开启压缩
enable_auto_clean = True #是否开启自动清理
compression_level = 2  # 自定义压缩等级 取值范围1~9，数字越大压缩文件越小，压缩时间越长。默认为2
# 压缩比2:1, 2级就压成一半大小

# 定时备份设置
daily_delete=1
weekly_delete=2
stop = False
maxtime = 60
time_counter = None

enable_cloud_backup = False
# baidu=ByPy() 
page = 1

TurnOffAutoSave = True
IgnoreSessionLock = True
WorldNames = [
    'world',
]
# 0:guest 1:user 2:helper 3:admin
MinimumPermissionLevel = {
    'make': 1,
    'start': 3,
    'status': 1,
    'stop': 2,
    'list': 1,
    'clean': 3
}

ServerPath = './server'
HelpMessage = '''
------ MCDR Regular Backup 20200529 ------
一个自定义时间的自动备份插件
§d【格式说明】§r
§7{0}§r 显示帮助信息
§7{0} make §e[<cmt>]§r 测试备份能力
§7{0} start §e[<cmt>]§r 开始每§e<cmt>§r分钟备份一次并打包存储
§7{0} status 查看rb的状态
§7{0} list §e[<cmt>]§r 查看备份列表
§7{0} clean 清理备份文件
§7{0} stop 关闭rb
'''.strip().format(Prefix)
game_saved = False  # 保存世界的开关
plugin_unloaded = False
creating_backup = Lock()


def copy_worlds(src, dst):  # 用来复制世界文件夹的
    def filter_ignore(path, files):
        return [file for file in files if file == 'session.lock' and IgnoreSessionLock]

    for world in WorldNames:
        shutil.copytree('{}/{}'.format(src, world), '{}/{}'.format(dst, world), ignore=filter_ignore)


def get_slot_folder(slot):  # 获取备份临时文件保存位置
    return '{}/temp{}'.format(BackupPath, slot)


def get_slot_info(slot):
    try:
        with open('{}/info.json'.format(get_slot_folder(slot))) as f:
            info = json.load(f, encoding='utf8')
        for key in info.keys():
            value = info[key]
    except:
        info = None
    return info


def format_time():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def format_slot_info(info_dict=None, slot_number=None):
    if type(info_dict) is dict:
        info = info_dict
    elif type(slot_number) is not None:
        info = get_slot_info(slot_number)
    else:
        return None

    if info is None:
        return None
    msg = '日期: {}; 注释: {}'.format(info['time'], info.get('comment', '§7空§r'))
    return msg


def rb_list(server, info, size_display=SizeDisplay):
    global page
    temp_zipPath = BackupPath + "/Backup_file"
    files = os.listdir(temp_zipPath)
    count = len(files)
    def get_dir_size(dir):
        size = 0
        for root, dirs, files in os.walk(dir):
            size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
        if size < 2 ** 30:
            return f'{round(size / 2 ** 20, 2)} MB'
        else:
            return f'{round(size / 2 ** 30, 2)} GB'
    def get_file_size(filePath):
        size = os.path.getsize(filePath)
        if size < 2 ** 30:
            return f'{round(size / 2 ** 20, 2)} MB'
        else:
            return f'{round(size / 2 ** 30, 2)} GB'

    # 显示备份列表，即temp_zipPath目录下文件列表 需要用for循环输出
    def show_files_size():
        num = (page-1)*5
        if num+5 > count:
            end = count
        else:
            end = num + 5
        for i in range(num, end, 1):
            print_message(server, info, "第§a{}§r个备份: {} 占用空间: §a{}§r".format(i+1, files[i],get_file_size(temp_zipPath+"/"+files[i])))

    if size_display:
        show_files_size()
        if count%5==0:
            max_page=count//5
        else:
            max_page=count//5+1
        if page == max_page:
            print_message(server, info, "共§a{}§r个备份,当前§a{}§r/§a{}§r页".format(str(count),str(page),str(max_page)), prefix="")
        else:
            next_page = page+1
            print_message(server, info, "共§a{}§r个备份,当前§a{}§r/§a{}§r页,输入§a{} list {}§r跳转到下一页".format(str(count),str(page),str(max_page),Prefix,str(next_page)), prefix="")
        print_message(server, info, '备份总占用空间: §a{}§r'.format(get_dir_size(temp_zipPath)), prefix='')


def print_message(server, info, msg, tell=True, prefix='[RB] '):  # 输出信息方法
    msg = prefix + msg
    if info.is_player and not tell:
        server.say(msg)
    else:
        server.reply(info, msg)


def print_help_message(server, info):
    for line in HelpMessage.splitlines():
        prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(Prefix), line)
        if prefix is not None:
            print_message(server, info, RText(line).set_click_event(RAction.suggest_command, prefix.group()), prefix='')
        else:
            print_message(server, info, line, prefix='')


def touch_backup_folder():
    def mkdir(path):
        if not os.path.exists(path):
            os.mkdir(path)

    mkdir(BackupPath)
    for i in range(SlotCount):
        mkdir(get_slot_folder(i + 1))


def create_backup_temp(server, info, comment):
    global creating_backup
    acquired = creating_backup.acquire(blocking=False)
    if not acquired:
        print_message(server, info, '正在§a备份§r中，请不要重复输入')
        return
    try:
        print_message(server, info, '§a备份§r中...请稍等')
        start_time = time.time()
        touch_backup_folder()

        # remove the last backup
        shutil.rmtree(get_slot_folder(SlotCount))

        # move temp i-1 to temp i
        for i in range(SlotCount, 1, -1):
            os.rename(get_slot_folder(i - 1), get_slot_folder(i))

        # start backup
        global game_saved, plugin_unloaded
        game_saved = False
        if TurnOffAutoSave:
            server.execute('save-off')
        server.execute('save-all')
        while True:
            time.sleep(0.01)
            if game_saved:
                break
            if plugin_unloaded:
                server.reply(info, '插件重载，§a备份§r中断！')
                return
        slot_path = get_slot_folder(1)

        copy_worlds(ServerPath, slot_path)
        slot_info = {'time': format_time()}
        if comment is not None:
            slot_info['comment'] = comment
        with open('{}/info.json'.format(slot_path), 'w') as f:
            json.dump(slot_info, f, indent=4)
        end_time = time.time()
        print_message(server, info, '§a备份§r完成，耗时§6{}§r秒'.format(round(end_time - start_time, 1)))
        print_message(server, info, format_slot_info(info_dict=slot_info))
        if enable_compression:
            print_message(server, info, '§a压缩§r中...请稍等')
            time.sleep(0.5)

            zip_folder(slot_path)
            print_message(server, info, '§a压缩§r完成')
    except Exception as e:
        print_message(server, info, '§a备份§r失败，错误代码{}'.format(e))
    finally:
        creating_backup.release()
        if TurnOffAutoSave:
            server.execute('save-on')


# 清理计时 （改秒计时为分计时）
def rb_start(server, info):
    global stop
    global maxtime
    global time_counter
    stop = True
    server.say('§7[§9Regular§r/§cBackup§7] §c定时备份以 §e{} §b分间隔开始运行'.format(maxtime))
    maxtimei = int(maxtime) * 60
    while stop:
        for time_counter in range(1, maxtimei):
            if stop:
                if maxtimei - time_counter == 1800:
                    server.say('§7[§9Regular§r/§cBackup§7] §b还有 §e30 §b分钟，定时备份')
                if maxtimei - time_counter == 300:
                    server.say('§7[§9Regular§r/§cBackup§7] §b还有 §e5 §b分钟，定时备份')
                    if enable_auto_clean:
                        clean_old_backups()
                time.sleep(1)
            else:
                return
        create_backup_temp(server, info, None)


def clean_old_backups():
    try:
        temp_zipPath = BackupPath + "/Backup_file" # 获得压缩文件路径
        times = [] # 时间戳数组（与files[]一一对应）
        ready_to_delete = []  # 待删除文件列表
        files = os.listdir(temp_zipPath) # 获得文件列表
        count = len(files)
        for i in range(0, count, 1): # 获得时间戳并存储
            files[i] = temp_zipPath+"/"+files[i]
            times.append(date.fromtimestamp(os.path.getmtime(files[i])))
        
        time_now=date.today()
        
        counter = count - 1
        while counter >= 0: # 倒序遍历文件列表
            if (time_now-times[counter]).days > daily_delete: # 大于每天只保留一个备份的指定时间
                print(time_now,times[counter])
                if times[counter-1] == times[counter]: # 且两备份为同一天创建
                    ready_to_delete.append(files[counter-1]) # 删除较老的备份
                    del files[counter-1]
                    del times[counter-1] # 从当前文件列表中清除
            counter -= 1
        
        counter=len(files)-1

        while counter >= 0:
            if (time_now-times[counter]).days > weekly_delete : # 大于每天只保留一个备份的指定时间
                if (times[counter] - times[counter-1]).days <= 6: # 且两备份为同一周内创建
                    ready_to_delete.append(files[counter-1]) # 删除较老备份
                    del files[counter-1]
                    del times[counter-1]# 从当前文件列表中清除
            counter -=1

        del ready_to_delete[0]
        for i in range(0,len(ready_to_delete),1):
            print(i,ready_to_delete[i])
            os.remove(ready_to_delete[i]) # 执行删除动作
    except IndexError:
        print("No file to delete")
            

        

def rb_stop(server, info):
    global stop
    global time_counter
    if stop:
        stop = False
        server.say('§7[§9Regular§r/§cBackup§7] §b定时备份已停止')
        time_counter = None
    else:
        server.tell(info.player, '§7[§9Regular§r/§cBackup§7] §b定时备份未开启')


def zip_folder(dir):
    global BackupPath
    temp_zipPath = BackupPath + "/Backup_file"
    if not os.path.exists(temp_zipPath):
        os.mkdir(temp_zipPath)
    filename = serverName + str(time.strftime("%Y%m%d-%H%M%S", time.localtime()))
    pwd = os.getcwd()
    os.system("{}/plugins/7z.exe a -t7z {} {}/temp1/* -r -mx={} -m0=LZMA2 -ms=10m -mf=on -mhc=on -mmt=on".format(pwd,
                                                                                                                 pwd + "/" + temp_zipPath + "/" + filename,
                                                                                                                 pwd + "/" + BackupPath,
                                                                                                                 compression_level))


def on_info(server, info):  # 解析控制台信息
    global maxtime  # 用于!!rb status查询状态

    if not info.is_user:
        if info.content == 'Saved the game':
            global game_saved
            game_saved = True  # 保存世界的开关为开
        return

    # content：如果该消息是玩家的聊天信息，则其值为玩家的聊天内容。否则其值为原始信息除去时间/线程名等前缀信息后的字符串
    command = info.content.split()  # 将content以空格为分隔符(包含\n),分割成command数组
    if len(command) == 0 or command[0] != Prefix:  # len()得到字符长度
        return

    del command[0]
    # cmd_len = len(command)
    # MCDR permission check
    '''global MinimumPermissionLevel
    if cmd_len >= 2 and command[0] in MinimumPermissionLevel.keys():
        if server.get_permission_level(info) < MinimumPermissionLevel[command[0]]:
            print_message(server, info, '§c权限不足！§r')
            return'''

    # !!rb
    if len(command) == 0:
        print_help_message(server, info)

    # !!rb make [<comment>]
    elif len(command) >= 1 and command[0] == 'make':
        print_message(server, info, "检测到!!rb make")
        comment = info.content.replace('{} make'.format(Prefix), '', 1).lstrip(' ')
        create_backup_temp(server, info, comment if len(comment) > 0 else None)

    # !!rb start [<Regular_time>]
    elif len(command) in [1, 2] and command[0] == 'start':
        print_message(server, info, "检测到!!rb start")
        if stop:
            server.tell(info.player, '§7[§9Regular§r/§cBackup§7] §c定时备份已在运行，请勿重复开启')
            return
        elif len(command) == 2:
            if command[1].isdigit():
                if 6 <= int(command[1]) <= 360:
                    maxtime = command[1]
                    rb_start(server, info)
                else:
                    server.tell(info.player, '§7[§9Regular§r/§cBackup§7] §c请输入 §l§e60-360 §r§c之间的整数')
                    return
            else:
                server.tell(info.player, '§7[§9Regular§r/§cBackup§7] §c请输入 §l§e45-360 §r§c之间的整数')
                return
        else:
            maxtime = command[1] if len(command) == 2 else '60'
            rb_start(server, info)

    # !!rb status 状态查询
    elif len(command) == 1 and command[0] == 'status':
        print_message(server, info, "检测到!!rb status")
        server.tell(info.player, '§7--------§bRegular Backup§7--------')
        server.tell(info.player, '§b定时备份状态：§e{}'.format(stop))
        if stop:
            server.tell(info.player, '§b定时备份间隔：§e{} min'.format(maxtime))
            server.tell(info.player, '§b离下次备份还剩: §e{} min'.format(int(int(maxtime) * 60 - time_counter) // 60))

    # !!rb list
    elif len(command) >= 1 and command[0] == 'list':
        global page
        print_message(server, info, "检测到!!rb list")
        if len(command) == 1:
            page = 1
            rb_list(server, info)
        elif command[1].isdigit():
            page = int(command[1])
            rb_list(server,info)


    # !!rb stop
    elif len(command) == 1 and command[0] == 'stop':
        print_message(server, info, "检测到!!rb stop")
        rb_stop(server, info)

    # !!rb clean
    elif len(command) == 1 and command[0] == 'clean' and enable_auto_clean:
        print_message(server, info, "检测到!!rb clean")
        clean_old_backups()
