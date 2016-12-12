#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys
import os
import requests
from lxml import etree
import re
import chardet
import codecs


filecoding = 'utf-8'
stdiocoding = sys.getfilesystemencoding()
webcoding = 'utf-8'

d_header = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0',
    'Accept-encoding': 'gzip',
}

PlayResX = 1920
PlayResY = 1080

ScriptInfo = '''[Script Info]
Title: Default Aegisub file
Original Script: 嗶哩嗶哩 - ( ゜- ゜)つロ 乾杯~
ScriptType: v4.00+
Collisions: Normal
PlayResX: %s
PlayResY: %s
''' % (PlayResX, PlayResY)

Styles = '''[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,微软雅黑,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0.00,0.00,1,2.00,0.00,2,30,30,120,0
Style: Danmaku,微软雅黑,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0.00,0.00,1,1.00,0.00,2,30,30,30,0
'''

Events = '''[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''


class Msg():
    ''' 定义弹幕类 '''
    d_msgcount = {'count': 0, '1': 0, '4': 0, '5': 0, 'x': 0}     # 记录弹幕类别的字典
    # 记录相同某一秒内的普通弹幕条数的字典
    d_regularcount_of_sec = {}
    # 记录相同某一秒内的顶/底部弹幕条数的字典
    d_topbtmcount_of_sec = {}

    def __init__(self, mode, time_offset, time_stamp, fontsize, color, message):
        self._mode = mode
        self._time_offset = time_offset
        self._time_stamp = time_stamp
        self._fontsize = fontsize
        self._color = hex(int(color))[2:].upper()
        self._message = message

        # 类内共享的临时变量
        self.f_time_offset = float(self._time_offset)
        self.i_time_offset = int(self.f_time_offset)  # 当前msg对象秒数的整数值
        self.i_msglen = len(self._message)             # 弹幕字符长度

        # count msg by type
        Msg.d_msgcount['count'] += 1
        Msg.d_msgcount[self._mode] += 1

        # count msg by type and second
        if (self._mode, self.i_time_offset) not in Msg.d_regularcount_of_sec:
            Msg.d_regularcount_of_sec[(self._mode, self.i_time_offset)] = 1
        else:
            Msg.d_regularcount_of_sec[(self._mode, self.i_time_offset)] += 1

    def __str__(self):
        # print self._message
        return (self._mode + self._time_offset + self._time_stamp + self._fontsize + self._color + self._message).encode(stdiocoding)

    def msg_fmt_ass_time(self, i_time_interval):
        ''' 弹幕时间转换成ass格式的时间 '''
        s_time_start = time.strftime(
            '%X', time.gmtime(self.f_time_offset))[1:] + '.00'
        s_time_end = time.strftime(
            '%X', time.gmtime(self.f_time_offset + i_time_interval))[1:] + '.00'
        return (s_time_start, s_time_end)

    def msg_fmt_ass(self):
        ''' 弹幕对象转换成ass dialogue '''
        s_type = 'Danmaku'
        s_name = ''
        s_margin_l = s_margin_r = s_margin_v = '0000'
        s_effect = ''
        s_text_color = '' if self._color == 'FFFFFF' else '\c&H' + self._color + '&'  # 颜色属性
        if self._mode == '1':
            i_time_interval = 15  # speed
            s_time_start, s_time_end = self.msg_fmt_ass_time(i_time_interval)
            i_resy_offset = Msg.d_regularcount_of_sec[
                (self._mode, self.i_time_offset)] * 32  # 当前msg对象的滚动行位置
            t_text_move = (                            # move属性,弹幕移动的参数元组
                PlayResX + self.i_msglen * 16,         # 弹幕初始位置的垂直偏移
                i_resy_offset,                         # 初始位置的水平偏移
                -1 * self.i_msglen * 16,               # 结束位置的垂直偏移
                i_resy_offset,                         # 结束位置的水平偏移
            )
            s_text = '{' + s_text_color + '\move' + \
                str(t_text_move) + '}' + self._message
        elif self._mode == '4' or self._mode == '5':
            i_time_interval = 5  # display span
            s_time_start, s_time_end = self.msg_fmt_ass_time(i_time_interval)
            for i in range(self.i_time_offset, self.i_time_offset + i_time_interval):
                # 将字幕出现时间之后的5个秒数 弹幕计数全部加一
                if (self._mode, i) not in Msg.d_topbtmcount_of_sec:
                    Msg.d_topbtmcount_of_sec[(self._mode, i)] = 1
                else:
                    Msg.d_topbtmcount_of_sec[(self._mode, i)] += 1
            i_resy_offset = Msg.d_topbtmcount_of_sec[
                (self._mode, self.i_time_offset)] * 32
            i_resy_offset = i_resy_offset if self._mode == '5' else PlayResY - i_resy_offset
            t_text_move = (PlayResX / 2, i_resy_offset)
            s_text = '{' + s_text_color + '\pos' + \
                str(t_text_move) + '}' + self._message
        else:
            pass
        return 'Dialogue: %s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (
            self._mode, s_time_start, s_time_end, s_type,
            s_name, s_margin_l, s_margin_r, s_margin_v,
            s_effect, s_text
        )


def checkaccess(s_html):
    ''' 判断页面是否需要先登录 '''
    assert s_html.find(
        r'div class="z-msg"') < 0, "It must be logged before parse this page!"


def checkindex(s_html, s_av):
    ''' 判断页面是否是多个视频列表的索引页 '''
    dom = etree.HTML(s_html)
    sel = dom.xpath('//html')[0]

    s_tag_plist = '//div[@class="player-wrapper"]/div[@class="main-inner"]/div[@class="v-plist"]/div[@id="plist"]/select/option/@value'
    l_plist_href = sel.xpath(s_tag_plist)
    f_complete_url = lambda x: 'http://www.bilibili.com' + x
    l_url = map(f_complete_url, l_plist_href)
    return l_url


def parse_cid(s_html):
    ''' 获取视频的弹幕文件的cid '''
    checkaccess(s_html)

    dom = etree.HTML(s_html)
    sel = dom.xpath('//html')[0]

    s_tag_title = '//div[@class="v-title"]/h1/text()'
    s_tag1 = '//div[@class="player-wrapper"]/div[@class="scontent"]/iframe/@src'
    s_tag2 = '//div[@class="player-wrapper"]/div[@class="scontent"]/script/text()'

    l_tag_title = sel.xpath(s_tag_title)
    s_title = l_tag_title[0]

    l_tag_src = sel.xpath(s_tag1)
    if l_tag_src:
        s_tmp = l_tag_src[0]
    else:
        l_script_text = sel.xpath(s_tag2)
        s_tmp = l_script_text[0]
    s_cid = re.findall(r'cid=(\d+)&aid', s_tmp)[0]
    return s_title, s_cid


def get_danmaku(s_cid):
    ''' 获取xml弹幕 '''
    s_url_danmaku = 'http://comment.bilibili.com/' + s_cid + '.xml'
    data_danmaku = requests.get(s_url_danmaku, headers=d_header)
    s_xml_danmaku = data_danmaku.text.encode(
        filecoding)  # unicode -> filecoding
    return s_xml_danmaku


def save_ass(s_xml_danmaku, s_save_ass):
    ''' xml弹幕保存成ass文件 '''
    dom = etree.XML(s_xml_danmaku)
    sel = dom.xpath('//i')[0]

    fd = codecs.open(s_save_ass, 'w', stdiocoding)
    fd.write((ScriptInfo + '\n' + Styles + '\n' + Events).decode(filecoding))

    s_tag_line = 'd'
    sel_line = sel.xpath(s_tag_line)
    for l in sel_line:
        l_tmp = l.get('p').split(',')
        s_time_offset = l_tmp[0]
        s_mode = l_tmp[1]    # 1:regular 4:bottom 5:top
        s_fontsize = l_tmp[2]
        s_color = l_tmp[3]
        s_time_stamp = l_tmp[4]
        # s_pool = l_tmp[5]    # unknow
        # s_user_id = l_tmp[6] # guess
        # s_msg_id = l_tmp[7]  # guess
        m = Msg(s_mode, s_time_offset, s_time_stamp,
                s_fontsize, s_color, l.text)
        print m
        fd.write(m.msg_fmt_ass() + '\n')
    fd.close()
    print Msg.d_msgcount


def main():
    s_av = sys.argv[1]
    s_url = 'http://www.bilibili.com/av' + s_av

    d_cid = {}
    data = requests.get(s_url, headers=d_header)
    s_html = data.text.encode(
        filecoding)  # unicode -> filecoding
    print 'Get page!', len(s_html)

    l_url = checkindex(s_html, s_av)
    if l_url:
        print 'This is a index page, find url lists:'
        for u in l_url:
            print u
            data_tmp = requests.get(u, headers=d_header)
            s_html_tmp = data_tmp.text
            print 'Get page!', len(s_html_tmp)
            s_title_tmp, s_cid_tmp = parse_cid(s_html_tmp)
            d_cid[s_title_tmp] = s_cid_tmp
    else:
        s_title, s_cid = parse_cid(s_html)
        d_cid[s_title] = s_cid
    print 'Get chainid!', d_cid

    s_save_path = s_av
    if not os.path.exists(s_save_path):
        os.makedirs(s_save_path)
    for (t, c) in d_cid.items():
        s_save_ass = s_save_path + '/' + c + '.ass'
        print s_save_ass, chardet.detect(s_save_ass)
        s_xml_danmaku = get_danmaku(c)
        print 'Get danmaku!', len(s_xml_danmaku)
        save_ass(s_xml_danmaku, s_save_ass)


if __name__ == '__main__':
    main()
