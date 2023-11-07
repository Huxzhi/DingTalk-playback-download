import shutil
import requests
import os
import sys
import re
import time

"""
## 使用说明：

1. 保存文件名为 "名称.机房.m3u8" , 可以保存多个文件，脚本会批量处理 。sz 表示深圳，bj 表示北京，注意修改
2. 执行脚本 "python3 a.py"

格式: "python3 a.py [-mac-crf] [-nv]" 在 mac 下 ，可以增加参数执行命令 -crf 压缩成 720p分辨率 ，-nv 提取音频

## 常用脚本

合并视频 Terminal 执行，已经包含在自动化脚本里面
ffmpeg -f concat -safe 0 -i file.txt -c copy a.mp4

压缩当前文件下的所有视频的
find ./ -name '*.mp4' -and ! -name '*264].mp4'  -exec sh -c 'ffmpeg -i "$0" -c:v libx264 -crf 30 -c:a aac "${0%%.mp4}[x264].mp4"' {} \;

"""

# sz 表示深圳，bj 表示北京，注意修改

host_room = "bj"  # 会重新赋值
cache_dir_base = "[dingtalk-playback]-cache-"
# base_url = f"https://dtliving-{jifang}.dingtalk.com/live_hp/"


def get_m3u8_list():
    file_list = []
    path = os.listdir('./')
    for i in path:
        if re.match(r".*\.m3u8$", i) and os.path.isfile(i):
            print(i)
            file_list.append(i)
    return file_list


def get_url(fileName, host_room="bj"):
    base_url = f"https://dtliving-{host_room}.dingtalk.com/live_hp/"
    url_list = []
    with open(fileName, "r") as f:
        s = f.readlines()
    for i in s:
        if re.match(r".*?ts.*?", i):
            url_list.append(base_url + i)
    return url_list


def download(fileName, host_room, cache_dir):
    urls = get_url(fileName, host_room)
    sum = len(urls)
    size = 0  # 单位 B
    scale = 50  # 进度条长度
    print(f"一共{sum}个ts文件下载")
    print("执行开始，祈祷不报错".center(scale // 2, "-"))
    start = time.perf_counter()

    finished_i = 0
    if os.path.exists(cache_dir):
        print("检测到已下载的文件，继续下载。。。")
        finished_i = max(len(os.listdir(cache_dir)) - 1, 0)
    else:
        os.mkdir(cache_dir)

    for i, url in enumerate(urls):

        if i < finished_i:
            # 已下载
            continue
        # 为了展示进度条
        a = "*" * round(i / sum * scale)
        b = "." * round((sum - i)/sum * scale)
        c = (i / sum) * 100
        dur = time.perf_counter() - start
        speed = float(size / 1024 / dur)
        db = "KB/s"
        # 核心代码 start
        with open(f"{cache_dir}/{i + 1}.ts", "wb") as f:
            response = requests.get(url[:-1])  # 去掉换行符

            if response.headers["Content-Type"] == "video/MP2T":  # 判断是否响应成功
                size += int(response.headers["Content-Length"])
                f.write(response.content)
            else:
                print(f"执行到 {i} 发生错误")
                print(
                    f"\n\nerror: response.Content-Type not 'video/MP2T' \nMaybe {fileName}'s roomID 'bj' or 'sz' miss")
                raise
        # end
        if speed > 1024:
            speed = float(speed / 1024)
            db = "MB/s"

        print(
            "\r[下载进度] {}/{} {:^3.0f}% [{}->{}] {:.2f}{} {:.2f}s ".format(i+1, sum, c, a, b, speed, db, dur), end="")
        # print(f"{i}/{sum} 已下载：{round(i/sum*100)}%", "ok")
        # time.sleep(1)
    return len(urls)


# 整合文件名, 方便FFmpeg合并
def parse_filename(cache_dir, len):
    base_path = os.getcwd()
    with open(f"{cache_dir}/file.txt", "w+") as f:
        for i in range(1, 1 + len):
            path = f"file '{base_path}/{cache_dir}/{i}.ts'\n"
            f.write(path)


def downloadAndConcat(fileName):
    cache_dir = cache_dir_base+fileName

    name = fileName.split('.', 2)[0]
    host_room = fileName.split('.', 2)[1]
    print(f"\n\n{fileName},准备下载...")
    for i in range(3):
        print("倒计时：", 3-i, "s")
        time.sleep(1)
    parse_filename(cache_dir, download(fileName, host_room, cache_dir))
    print("\ndownload finished,准备合并视频...")
    time.sleep(3)  # 等待喵
    os.system(
        f'ffmpeg -hide_banner -f concat -safe 0 -i {cache_dir}/file.txt -c copy {name}.mp4')
    os.rename(fileName, fileName+'.ok')

    # 清除缓存
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    print(f"{fileName} finished")

    return fileName


def extraFFmpeg(fileNames, argv):
    for fileName in fileNames:
        name = fileName.split('.', 2)[0]
        # 压缩视频
        if "-mac-crf" in argv:
            os.system(
                f"ffmpeg -hide_banner  -y -i {name}.mp4 -vf scale=-1:720  -c:v libx264 -crf 30 -c:a aac '{name}[x264].mp4'")
        # 提取音频
        if "-vn" in argv:
            os.system(
                f"ffmpeg -hide_banner  -y -i {name}.mp4 -vn -c:a copy '{name}.aac'")


if __name__ == "__main__":
    list = get_m3u8_list()
    finished = []

    print("检测到可下载文件： ", list)

    for fileName in list:
        finished.append(downloadAndConcat(fileName))

    # 对已下载完成的视频进行额外操作
    extraFFmpeg(finished, sys.argv)
