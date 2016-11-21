## Description
下载bilibili弹幕并转换成ass字幕的脚本

## Install
pip install lxml
> 安装lxml前有部分依赖包需要安装,[参考](http://lxml.de/installation.html#requirements)

## Using
```
%prog 4682356            # 直接跟av号
```
> 支持普通弹幕,顶部和底部弹幕,支持颜色属性,字幕保存在`<avid>/<cid>.ass`<br>
部分页面内容需要先登录才能获取,暂时不支持<br>
部分页面有多个视频,支持所有视频的字幕下载<br>

下载相应的视频文件,改成一致的名字,使用播放其打开即可加载字幕
![](https://raw.githubusercontent.com/hurdonkey/bilibilitest/master/img/test.jpg)

## Todo
(1)视频文件的下载合并
