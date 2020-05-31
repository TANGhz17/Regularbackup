# coding: utf8
import os
import re
import shutil
import time
from threading import Lock
from utils.rtext import *
import json

# from bypy import ByPy

# rb本体设置
SlotCount = 2
Prefix = '!!rb'
BackupPath = './rb_temp'
serverName = ""  # 压缩文件的名称前半段，后半段是时间
compression_level = 5 # 自定义压缩等级 取值范围1~9，数字越大压缩文件越小，压缩时间越长。默认为5

# 定时备份设置
stop = False
maxtime = 60
time_counter = None

enable_cloud_backup = False
# baidu=ByPy() 

TurnOffAutoSave = True
IgnoreSessionLock = True
WorldNames = [
    'world',
]
# 0:guest 1:user 2:helper 3:admin
MinimumPermissionLevel = {
    'start': 1
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
                time.sleep(1)
            else:
                return
        create_backup_temp(server, info, None)


def rb_stop(server, info):
    global stop
    global time_counter
    if stop:
        stop = False
        server.say('§7[§9Regular§r/§cBackup§7] §b定时备份已停止')
        time_counter = None
    else:
        server.tell(info.player, '§7[§9Regular§r/§cBackup§7] §b定时备份未开启')


# def zip_folder(dir):
#     global BackupPath
#     temp_zipPath = BackupPath + "/Backup_file"
#     if not os.path.exists(temp_zipPath):
#         os.mkdir(temp_zipPath)
#     filename = serverName + str(time.strftime("%Y%m%d-%H%M%S", time.localtime()))
#     zipf = zipfile.ZipFile("{}/{}.zip".format(temp_zipPath, filename), 'w')
#     for root, dirs, files in os.walk(dir):
#         # print(root.replace(BackupPath,""))
#         rootpath = root.replace(dir, "")
#         rootpath = rootpath and rootpath + os.sep or ""
#         for file in files:
#             zipf.write(os.path.join(root, file), rootpath + file)
#     zipf.close()

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
                if 60 <= int(command[1]) <= 360:
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

    # !!rb stop
    elif len(command) == 1 and command[0] == 'stop':
        print_message(server, info, "检测到!!rb stop")
        rb_stop(server, info)

    # !!rb status 状态查询
    elif len(command) == 1 and command[0] == 'status':
        print_message(server, info, "检测到!!rb status")
        server.tell(info.player, '§7--------§bRegular Backup§7--------')
        server.tell(info.player, '§b定时备份状态：§e{}'.format(stop))
        if stop:
            server.tell(info.player, '§b定时备份间隔：§e{} min'.format(maxtime))
            server.tell(info.player, '§b离下次备份还剩: §e{} min'.format(int(int(maxtime) * 60 - time_counter) // 60))
