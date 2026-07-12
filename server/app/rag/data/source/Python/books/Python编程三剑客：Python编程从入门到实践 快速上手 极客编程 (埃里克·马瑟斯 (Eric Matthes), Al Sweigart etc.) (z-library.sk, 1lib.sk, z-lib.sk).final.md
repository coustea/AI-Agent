# Python编程三剑客：Python编程从入门到实践 快速上手 极客编程 (埃里克 马瑟斯 (Eric Matthes), Al Sweigart etc.) (z-library.sk, 1lib.sk, z-lib.sk)

# 版权信息书名：Python编程快速上手--让繁琐工作自动化

ISBN：978-7-115-42269-9

本书由人民邮电出版社发行数字版。版权所有，侵权必究。

您购买的人民邮电出版社电子书仅供您个人使用，未经授权，不得以任何方式复制和传播本书内容。

我们愿意相信读者具有这样的良知和觉悟，与我们共同保护知识产权。

如果购买者有侵权行为，我们可能对该用户实施包括但不限于关闭该帐号等维权措施，并可能追究法律责任。

- 著 [美] Al Sweigart

译王海鹏责任编辑陈冀康

- 人民邮电出版社出版发行北京市丰台区成寿寺路11号邮编 100164 电子邮件 315@ptpress.com.cn

网址 http://www.ptpress.com.cn

- 读者服务热线：(010)81055410

反盗版热线：(010)81055315

# 版权声明

Simplified Chinese-language edition copyright © 2016 by Posts and Telecom Press.

Copyright © 2015 by Al Sweigart.Title of English-language original: Automate The Boring Stuff with Python ISBN-13: 978-1-59327-599-0, published by No Starch Press.

All rights reserved.

本书中文简体字版由美国No Starch出版社授权人民邮电出版社出版。未经出版者书面许可，对本书任何部分不得以任何方式复制或抄袭。

版权所有，侵权必究。

# 内容提要如今，人们面临的大多数任务都可以通过编写计算机软件来完成。Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。通过Python编程，我们能够解决现实生活中的很多任务。

本书是一本面向实践的Python编程实用指南。本书的目的，不仅是介绍Python语言的基础知识，而且还通过项目实践教会读者如何应用这些知识和技能。本书的第一部分介绍了基本的Python编程概念，第二部分介绍了一些不同的任务，通过编写Python程序，可以让计算机自动完成它们。第二部分的每一章都有一些项目程序，供读者学习。每章的末尾还提供了一些习题和深入的实践项目，帮助读者巩固所学的知识。附录部分提供了所有习题的解答。

本书适合任何想要通过Python学习编程的读者，尤其适合缺乏编程基础的初学者。通过阅读本书，读者将能利用最强大的编程语言和工具，并且将体会到Python编程的快乐。

# 作者简介

Al Sweigart是一名软件开发者和技术图书作者，居住在旧金山。Python是他最喜欢的编程语言，他开发了几个开源模块。他的其他著作都在他的网站http://www. inventwithpython.com/ 上。

# 技术评审者简介

Ari Lacenski是Android应用程序和Python软件开发者。她住在旧金山，她写了一些关于Android编程的文章，放在http://gradlewhy.ghost.io/ 上，并与Women Who Code合作提供指导。她还是一个民谣吉他手。

# 致谢没有很多人的帮助，我不可能写出这样一本书。我想感谢Bill Pollock，我的编辑Laurel Chun、Leslie Shen、Greg Poulos和Jennifer Griffith-Delgado，以及No Starch Press的其他工作人员，感谢他们非常宝贵的帮助。感谢我的技术评审Ari Lacenski，她提供了极好的建议、编辑和支持。

非常感谢Guido van Rossum，以及Python软件基金会的每个人，感谢他们了不起的工作。Python社区是我在业界看到的最佳社区。

最后，我要感谢我的家人和朋友，以及在Shotwell的伙伴，他们不介意我在写这本书时忙碌的生活。干杯！

# 译者序会编程的人不一样这是机器代替人的时代，也是人控制机器的时代。这是程序员的时代，也是非程序员学编程的时代。这是算法的时代，也是编程语言的时代。翻译本书期间，深度学习的人工智能程序AlphaGo以4:1击败了李世石九段。

每一个不会编程的年轻人都应该认真考虑：是不是应该开始学习编程？

学习一门新的语言，总是让人感到畏缩。这让我想起大学时英语老师教的学习方法：听说领先，读写跟上。确实，学语言效果最好的方法就是"用"。本书就遵循了这样的宗旨。本书是面对编程初学者的书，假定读者没有任何编程知识。在简单介绍Python编程语言的基本知识后，就开始用一个接一个的例子，教我们如何用Python来完成一些日常工作，利用计算机这个强大的工具，节省工作时间，提高工作效率，避免手工操作容易带来的错误。

真正的程序员，用编程来解决自己和别人的问题。俄罗斯有一个程序员编写了一个程序，会给老婆发加班短信，会在宿醉不醒时给自己请假，会自动根据邮件恢复客户的数据库，还可以一键远程煮咖啡。加拿大一名零编程基础的农场主，在学习了一门编程课后，开发了一个程序，自动控制拖拉机，配合联合收割机收割谷物。

若是已经掌握了其他编程语言，想学习Python，本书也是不错的参考。每一种编程语言，都会提供一种独特的视角，让你对编程有新的认识。我非常喜欢Python没有花括号和分号，程序很"清爽"，符合奥卡姆剃刀原理：如无必要，勿增实体。本书并没有深入介绍面向对象和函数式编程范式，如果想了解Python这方面的内容，请参考其他书籍。

在本书的翻译过程，我自己也在项目中使用Python编程，从中得到许多启发。因此，郑重向大家推荐。翻译中的错误，请不吝指出。

王海鹏

2016年春于上海

## 本书的读者对象软件是我们今天使用的许多工具的核心：几乎每个人都使用社交网络来进行交流，许多人的手机中都有连接因特网的计算机，大多数办公室工作都涉及操作计算机来完成工作。因此，对编程人才的需求暴涨。无数的图书、交互式网络教程和开发者新兵训练营，承诺将有雄心壮志的初学者变成软件工程师，获得6位数的薪水。

本书不是针对这些人的。它是针对所有其他的人。

就它本身来说，这本书不会让你变成一个职业软件开发者，就像几节吉他课程不会让你变成一名摇滚巨星。但如果你是办公室职员、管理者、学术研究者，或使用计算机来工作或娱乐的任何人，你将学到编程的基本知识，这样就能将下面这样一些简单的任务自动化：

- 移动并重命名几千个文件，将它们分类，放入文件夹；

- 填写在线表单，不需要打字；

- 在网站更新时，从网站下载文件或复制文本；

- 让计算机向客户发出短信通知；

- 更新或格式化Excel电子表格；

- 检查电子邮件并发出预先写好的回复。

对人来说，这些任务简单，但很花时间。它们通常很琐碎、很特殊，没有现成的软件可以完成。有一点编程知识，就可以让计算机为你完成这些任务。

## 什么是编程在电视剧和电影中，常常看到程序员在闪光的屏幕上迅速地输入密码般的一串1和0，但现代编程没有这么神秘。编程只是输入指令让计算机来执行。这些指令可能运算一些数字，修改文本，在文件中查找信息，或通过因特网与其他计算机通信。

所有程序都使用基本指令作为构件块。下面是一些常用的指令，用自然语言的形式来表示：

"做这个，然后做那个。"

"如果这个条件为真，执行这个动作，否则，执行那个动作。"

"按照指定次数执行这个动作。"

"一直做这个，直到条件为真。"

也可以组合这些构件块，实现更复杂的决定。例如，这里有一些编程指令，称为源代码，是用Python编程语言编写的一个简单程序。从头开始，Python软件执行每行代码（有些代码只有在特定条件为真时执行，否则Python会执行另外一些代码），直到到达底部。1. passwordFile = open('SecretPasswordFile.txt') 2. secretPassword = passwordFile.read() 3. print('Enter your password.') typedPassword = input() 4. if typedPassword == secretPassword: 5. print('Access granted') 6. if typedPassword == '12345': 7. print('That password is one that an idiot puts on their luggage.') else: 8. print('Access denied')

你可能对编程一无所知，但读了上面的代码，也许就能够合理地猜测它做的事。首先，打开了文件SecretPasswordFile.txt1. ，读取了其中的密码2. 。然后，提示用户（通过键盘）输入一个密码3. 。比较这两个密码4. ，如果它们一样，程序就在屏幕上打印Access granted5. 。接下来，程序检查密码是否为123456. ，提示说这可能并不是最好的密码7. 。如果密码不一样，程序就在屏幕上打印Access denied8. 。

### 什么是Python

Python指的是Python编程语言（包括语法规则，用于编写被认为是有效的Python代码），以及Python解释器软件，它读取源代码（用python语言编写），并执行其中的指令。Python解释器可以从http://python.org/免费下载，有针对Linux、OS X和Windows的版本。

Python的名字来自于英国超现实主义喜剧团体，而不是来自于蛇。Python程序员被亲切地称为Pythonistas。Monty Python和与蛇相关的引用常常出现在Python的指南和文档中。

### 程序员不需要知道太多数学我听到的关于学习编程的最常见的顾虑，就是人们认为这需要很多数学知识。其实，大多数编程需要的数学知识不超过基本算数。实际上，善于编程与善于解决数独问题没有太大差别。

要解决数独问题，数字1到9必须填入9×9的棋盘上每一行、每一列，以及每个3×3的内部方块。通过推导和起始数字的逻辑，你会找到一个答案。例如，在图 1的数独问题中，既然5出现在了左上角，它就不能出现在顶行、最左列，或左上角3×3方块中的其他位置。每次解决一行、一列或一个方块，将为剩下的部分提供更多的数字线索。

仅仅因为数独使用了数字，并不意味着必须精通数学才能求出答案。编程也是这样。就像解决数独问题一样，编程需要将一个问题分解为单个的、详细的步骤。类似地，在调试程序时（即寻找和修复错误），你会耐心地观察程序在做什么，找出缺陷的原因。像所有技能一样，编程越多，你就掌握得越好。

图1 一个新的数独问题（左边）及其答案（右边）。尽管使用了数字，数独并不需要太多数学知识

### 编程是创造性活动编程是一项创造性任务，有点类似于用乐高积木构建一个城堡。你从基本的想法开始，希望城堡看起来像怎样，并盘点可用的积木。然后开始构建。在你完成构建程序后，可以让代码变得更美观，就像对你的城堡那样。

编程与其他创造性活动的不同之处在于，在编程时，你需要的所有原材料都在计算机中，你不需要购买额外的画布、颜料、胶片、纱线、乐高积木或电子器件。在程序写好后，很容易将它在线共享给整个世界。尽管在编程时你会犯错，这项活动仍然很有乐趣。

## 本书简介本书的第一部分介绍了基本Python编程概念，第二部分介绍了一些不同的任务，你可以让计算机自动完成它们。第二部分的每一章都有一些项目程序，供你学习。下面简单介绍一下每章的内容。第一部分：Python编程基础

"第 1 章：Python基础"介绍了表达式、Python指令的最基本类型，以及如何使用Python交互式环境来尝试运行代码。

"第 2 章：控制流"解释了如何让程序决定执行哪些指令，以便代码能够智能地响应不同的情况。

"第3章：函数"介绍了如何定义自己的函数，以便将代码组织成可管理的部分。

"第4章：列表"介绍了列表数据类型，解释了如何组织数据。

"第 5 章：字典和结构化数据"介绍了字典数据类型，展示了更强大的数据组织方法。

"第6章：字符串操作"介绍了处理文本数据（在Python中称为字符串）。第二部分：自动化任务

"第7章：模式匹配与正则表达式"介绍了Python如何用正则表达式处理字符串，以及查找文本模式。

"第 8 章：读写文件"解释了程序如何读取文本文件的内容，并将信息保存到硬盘的文件中。

"第 9 章：组织文件"展示了Python如何用比手工操作快得多的速度，复制、移动、重命名和删除大量的文件，也解释了压缩和解压缩文件。

"第10章：调试"展示了如何使用Python的缺陷查找和缺陷修复工具。

"第 11 章：从Web抓取信息"展示了如何编程来自动下载网页，解析它们，获取信息。这称为从Web抓取信息。

"第 12 章：处理Excel电子表格"介绍了编程处理Excel电子表格，这样你就不必去阅读它们。如果你必须分析成百上千的文档，这是很有帮助的。

"第13章：处理PDF和Word文档"介绍了编程读取Word和PDF文档。

"第14章：处理CSV文件和JSON数据"解释了如何编程操作CSV和JSON文件。

"第15章：保持时间、计划任务和启动程序"解释了Python程序如何处理时间和日期，如何安排计算机在特定时间执行任务。这一章也展示了Python程序如何启动非Python程序。

"第16章：发送电子邮件和短信"解释了如何编程来发送电子邮件和短信。

"第17章：操作图像"解释了如何编程来操作JPG或PNG这样的图像。

"第18章：用GUI自动化控制键盘和鼠标"解释了如何编程控制鼠标和键盘，自动化鼠标点击和击键。

## 下载和安装Python

可以从http://python.org/downloads/免费下载针对Windows、OS X和Ubuntu的Python版本。如果你从该网站的下载页面下载了最新的版本，本书中的所有程序应该都能工作。

注意请确保下载Python 3的版本（诸如3.4.0）。本书中的程序将运行在Python 3上，有一部分程序在Python 2上也许不能正常运行。

你需要在下载页面上找到针对64位或32位计算机以及特定操作系统的Python安装程序，所以先要弄清楚你需要哪个安装程序。如果你的计算机是2007年或以后购买的，很有可能是64位的系统。否则，可能是32位的系统，但下面是确认的方法：

- 在Windows上。选择StartControlPanelSystem。检查系统类型是64位或32位。

- 在OS X上，进入Apple菜单，选择About This MacMoreInfoSystemReport Hardware，然后查看Processor Name字段。如果是Intel Core Solo或Intel Core Duo，机器是32位的。如果是其他（包括Intel Core 2 Duo），机器是64位的。

- 在Ubuntu Linux上，打开终端窗口，运行命令uname -m。结果是i686表示是32位，x86_64表示是64位。

在Windows上，下载Python安装程序（文件扩展名是.msi），并双击它。按照安装程序显示在屏幕上的指令来安装Python，步骤如下。

1．选择Install for All Users，然后点击Next。

2．通过点击Next安装到C:\Python34文件夹。

3．再次点击Next，跳过定制Python的部分。

在OS X上，下载适合你的OS X版本的.dmg文件，并双击它。按照安装程序显示在屏幕上的指令来安装Python，步骤如下。

1．当DMG包在一个新窗口中打开时，双击Python.mpkg文件。你可能必须输入管理员口令。

2．点击Continue，跳过欢迎部分，并点击Agree，接受许可证。

3．选择HD Macintosh（或者你的硬盘的名字），并点击Install。

如果使用的是Ubuntu，可以从终端窗口安装Python，步骤如下。

1．打开终端窗口。

2．输入sudo apt-get install python3。

3．输入sudo apt-get install idle3。

4．输入sudo apt-get install python3-pip。

## 启动IDLE

Python解释器是运行Python程序的软件，而交互式开发环境（IDLE）是输入程序的地方，就像一个字处理软件。现在让我们启动IDLE。

- 在Windows7或更新的版本上，点击屏幕左下角的开始图标，在搜索框中输入IDLE，并选择IDLE（Python GUI）。

- Windows XP上，点击开始按钮，然后选择ProgramsPython 3.4IDLE（Python GUI）。

- 在OS X上，打开Finder窗口，点击Applications，点击Python 3.4，然后点击IDLE的图标。

- 在Ubuntu上，选择ApplicationsAccessoriesTerminal，然后输入idle3（也许你也可以点击屏幕顶部的Applications，选择Programming，然后点击IDLE 3）。

### 交互式环境无论你使用什么操作系统，初次出现的IDLE窗口应该基本上是空的，除了类似下面这样的文本：Python 3.4.0 (v3.4.0:04f714765c13, Mar 16 2014, 19:25:23) [MSC v.1600 64 bit (AMD64)] on win32Type "copyright", "credits" or "license()" for more information. >>>

这个窗口称为交互式环境。这是让你向计算机输入指令的程序，很像OS X上的终端窗口，或Windows上的命令行提示符。Python的交互式环境让你输入指令，供Python解释器软件来执行。计算机读入你输入的指令，并立即执行它们。

例如，在交互式环境的>>>提示符后输入以下指令：>>> print('Hello world!')

在输入该行并按下回车键后，交互式环境将显示以下内容作为响应：>>> print('Hello world!') Hello world!

## 如何寻求帮助独自解决编程问题可能比你想的要容易。如果你不相信，就让我们故意产生一个错误：在交互式环境中输入'42' + 3。现在你不需要知道这条指令是什么意思，但结果看起来应该像这样：>>> '42' + 3 1. Traceback (most recent call last): File "<pyshell#0>", line 1, in <module> '42' + 3 2. TypeError: Can't convert 'int' object to str implicitly >>>

这里出现了错误信息2. ，因为Python不理解你的指令。错误信息的traceback部分1. 显示了Python遇到困难的特定指令和行号。如果你不知道怎样处理特定的错误信息，就在线查找那条错误信息。在你喜欢的搜索引擎上输入"TypeError: Can't convert 'int' object to str implicitly"（包括引号），你就会看到许多的链接，解释这条错误信息的含义，以及什么原因导致这条错误，如图2所示。

你常常会发现，别人也遇到了同样的问题，而其他乐于助人的人已经回答了这个问题。没有人知道编程的所有方面，所以所有软件开发者的工作，都是每天在寻找技术问题的答案。

图2 错误信息的Google搜索结果可能非常有用

## 聪明地提出编程问题如果不能在线查找到答案，请尝试在Stack Overlow（http://stackoverflow.com/ ）或"learnprogramming"subreddit（http://reddit.com/r/learnprogramming/ ）这样的论坛上提问。但要记住，用聪明的方式提出编程问题，这有助于别人来帮助你。确保阅读这些网站的FAQ（常见问题），了解正确的提问方式。

在提出编程问题时，要记住以下几点。

- 说明你打算做什么，而不只是你做了什么。这让帮助你的人知道你是否走错了路。

- 明确指出发生错误的地方。它是在程序每次启动时发生，还是在你做了某些动作之后？

- 将完整的错误信息和你的代码复制粘贴到http://pastebin.com/ 或http://gist. github.com/ 。

- 这些网站让你很容易在网上与他人共享大量的代码，而不会丢失任何文本格式。然后你可以将贴出的代码的URL放在电子邮件或论坛帖子中。例如，这里是我贴出的一些代码片段：http://pastebin.com/SzP2DbFx/ 和https://gist.github. com/ asweigart/6912168/ 。

- 解释你为了解决这个问题已经尝试了哪些方法。这会告诉别人你已经做了一些工作来弄清楚状况。

- 列出你使用的Python版本（Python 2解释器和Python3解释器之间有一些重要的区别）。而且，要说明你使用的操作系统和版本。

- 如果错误在你更改了代码之后出现，准确说明你改了什么。

- 说明你是否在每次运行该程序时都能重现该错误，或者它只是在特定的操作执行之后才出现。如果是这样，解释是哪些操作。

也要遵守良好的在线礼节。例如，不要全用大写提问，或者对试图帮助你的人提出无理的要求。

## 小结对于大多数人，他们的计算机只是设备，而不是工具。但通过学习如何编程，你就能利用现代社会中最强大的工具，并且你会一直感到快乐。编程不是脑外科手术，业余人士是完全可以尝试或犯错的。

我喜欢帮助人们探索Python。我在自己的博客上编写编程指南（http:// inventwithpython.com/blog/ ），你可以发邮件向我提问（al@inventwithpython.com）。

本书将从零编程知识开始，但你的问题可能超出本书的范围。记住如何有效地提问，知道如何寻找答案，这对你的编程之旅是无价的工具。

让我们开始吧！

# 第一部分 Python编程基础

# 第1章 Python基础

Python编程语言有许多语法结构、标准库函数和交互式开发环境功能。好在，你可以忽略大多数内容。你只需要学习部分内容，就能编写一些方便的小程序。

但在动手之前，你必须学习一些基本编程概念。就像魔法师培训，你可能认为这些概念既深奥又啰嗦，但有了一些知识和实践，你就能像魔法师一样指挥你的计算机，完成难以置信的事情。

本章有几个例子，我们鼓励你在交互式环境中输入它们。交互式环境让你每次执行一条Python指令，并立即显示结果。使用交互式环境对于了解基本Python指令的行为是很好的，所以你在阅读时要试一下。做过的事比仅仅读过的内容，更令人印象深刻。

## 1.1 在交互式环境中输入表达式启动IDLE就运行了交互式环境，这是和Python一起安装的。在Windows上，打开"开始"菜单，选择"All ProgramsPython 3.3"，然后选择"IDLE（Python GUI）"。在OS X上，选择"ApplicationsMacPython 3.3IDLE"。在Ubuntu上，打开新的终端窗口并输入idle3。

一个窗口会出现，包含>>>提示符，这就是交互式环境。在提示符后输入2 + 2，让Python做一些简单的算术。>>> 2 + 2 4

IDLE窗口现在应该显示下面这样的文本：Python 3.3.2 (v3.3.2:d047928ae3f6, May 16 2013, 00:06:53) [MSC v.1600 64 bit (AMD64)] on win32 Type "copyright", "credits" or "license()" for more information. >>> 2 + 2 4 >>>

在Python中，2 + 2称为"表达式"，它是语言中最基本的编程结构。表达式包含"值"（例如2）和"操作符"（例如+），并且总是可以求值（也就是归约）为单个值。这意味着在Python代码中，所有使用表达式的地方，也可以使用一个值。

在前面的例子中，2 + 2被求值为单个值4。没有操作符的单个值也被认为是一个表达式，尽管它求值的结果就是它自己，像下面这样：>>> 2 2

错误没关系！

如果程序包含计算机不能理解的代码，就会崩溃，这将导致Python显示错误信息。错误信息并不会破坏你的计算机，所以不要害怕犯错误。"崩溃"只是意味着程序意外地停止执行。

如果你希望对一条错误信息了解更多，可以在网上查找这条信息的准确文本，找到关于这个错误的更多内容。也可以查看http://nostarch.com/automatestuff/ ，这里有常见的Python错误信息和含义的列表。

Python表达式中也可以使用大量其他操作符。例如，表 1-1 列出了Python的所有数学操作符。

表1-1 数学操作符操作符操作例子求值为

**

指数

2 ** 3

%

取模/取余数

22 % 8

//

整除/商数取整

22 // 8

/

除法

22 / 8

2.75

*

乘法

3 * 5

-

减法

5 - 2

+

加法

2 + 2

数学操作符的操作顺序（也称为"优先级"）与数学中类似。**操作符首先求值，接下来是­*、/、//和%操作符，从左到右计算。+和-操作符最后求值，也是从左到右计算。如果需要，可以用括号来改变通常的优先级。在交互式环境中输入下列表达式：>>> 2 + 3 * 6 20 >>> (2 + 3) * 6 30 >>> 48565878 * 578453 28093077826734 >>> 2 ** 8 256 >>> 23 / 7 3.2857142857142856 >>> 23 // 7 3 >>> 23 % 7 2 >>> 2 + 2 4 >>> (5 - 1) * ((7 + 1) / (3 - 1)) 16.0

在每个例子中，作为程序员，你必须输入表达式，但Python完成较难的工作，将它求值为单个值。Python将继续求值表达式的各个部分，直到它成为单个值，如图1-1所示。

图1-1 表达式求值将它归约为单个值将操作符和值放在一起构成表达式的这些规则，是 Python 编程语言的基本部分，就像帮助我们沟通的语法规则一样。下面是例子：

This is a grammatically correct English sentence.

This grammatically is sentence not English correct a.

第二行很难解释，因为它不符合英语的规则。类似地，如果你输入错误的 Python指令，Python也不能理解，就会显示出错误信息，像下面这样：>>> 5 + File "<stdin>", line 1 5 + ^ SyntaxError: invalid syntax >>> 42 + 5 + * 2 File "<stdin>", line 1 42 + 5 + * 2 ^ SyntaxError: invalid syntax

你总是可以在交互式环境中输入一条指令，检查它是否能工作。不要担心会弄坏计算机：最坏的情况就是Python显示出错信息。专业的软件开发者在编写代码时，常常会遇到错误信息。

## 1.2 整型、浮点型和字符串数据类型记住，表达式是值和操作符的组合，它们可以通过求值成为单个值。"数据类型"是一类值，每个值都只属于一种数据类型。表1-2列出了Python中最常见的数据类型。例如，值-2和30属于"整型"值。整型（或int）数据类型表明值是整数。带有小数点的数，如3.14，称为"浮点型"（或float）。请注意，尽管42是一个整型，但42.0是一个浮点型。

表1-2 常见数据类型数据类型例子整型

-2, -1, 0, 1, 2, 3, 4, 5

浮点型

-1.25, -1.0, - -0.5, 0.0, 0.5, 1.0, 1.25

字符串

'a', 'aa', 'aaa', 'Hello!', '11 cats'

Python程序也可以有文本值，称为"字符串"，或strs（发音为"stirs"）。总是用单引号（'）包围住字符串（例如'Hello'或'Goodbye cruel world!'），这样Python就知道字符串的开始和结束。甚至可以有没有字符的字符串，称为"空字符串"。第4章更详细地解释了字符串。

如果你看到错误信息SyntaxError: EOL while scanning string literal，可能是忘记了字符串末尾的单引号，如下面的例子所示：>>> 'Hello world! SyntaxError: EOL while scanning string literal

## 1.3 字符串连接和复制根据操作符之后的值的数据类型，操作符的含义可能会改变。例如，在操作两个整型或浮点型值时，+是相加操作符。但是，在用于两个字符串时，它将字符串连接起来，成为"字符串连接"操作符。在交互式环境中输入以下内容：>>> 'Alice' + 'Bob' 'AliceBob'

该表达式求值为一个新字符串，包含了两个字符串的文本。但是，如果你对一个字符串和一个整型值使用加操作符，Python就不知道如何处理，它将显示一条错误信息。>>> 'Alice' + 42 Traceback (most recent call last): File "<pyshell#26>", line 1, in <module> 'Alice' + 42 TypeError: Can't convert 'int' object to str implicitly

错误信息Can't convert 'int' object to str implicitly表示Python认为，你试图将一个整数连接到字符串'Alice'。代码必须显式地将整数转换为字符串，因为Python不能自动完成转换。（1.6节"程序剖析"在讨论函数时，将解释数据类型转换。）

在用于两个整型或浮点型值时，­*­操作符表示乘法。但­*­操作符用于一个字符串值和一个整型值时，它变成了"字符串复制"操作符。在交互式环境中输入一个字符串乘一个数字，看看效果。>>> 'Alice' * 5 'AliceAliceAliceAliceAlice'

该表达式求值为一个字符串，它将原来的字符串重复若干次，次数就是整型的值。字符串复制是一个有用的技巧，但不像字符串连接那样常用。

*操作符只能用于两个数字（作为乘法），或一个字符串和一个整型（作为字符串复制操作符）。否则，Python将显示错误信息。>>> 'Alice' * 'Bob' Traceback (most recent call last): File "<pyshell#32>", line 1, in <module> 'Alice' * 'Bob' TypeError: can't multiply sequence by non-int of type 'str' >>> 'Alice' * 5.0 Traceback (most recent call last): File "<pyshell#33>", line 1, in <module> 'Alice' * 5.0 TypeError: can't multiply sequence by non-int of type 'float'

Python不理解这些表达式是有道理的：你不能把两个单词相乘，也很难将一个任意字符串复制小数次。

## 1.4 在变量中保存值

"变量"就像计算机内存中的一个盒子，其中可以存放一个值。如果你的程序稍后将用到一个已求值的表达式的结果，就可以将它保存在一个变量中。

### 1.4.1 赋值语句用"赋值语句"将值保存在变量中。赋值语句包含一个变量名、一个等号（称为赋值操作符），以及要存储的值。如果输入赋值语句spam = 42，那么名为spam的变量将保存一个整型值42。

可以将变量看成一个带标签的盒子，值放在其中，如图1-2所示。

图1-2 spam = 42 就像是告诉程序"变量spam现在有整数42放在里面"

例如，在交互式环境中输入以下内容：1. >>> spam = 40 >>> spam 40 >>> eggs = 2 2. >>> spam + eggs 42 >>> spam + eggs + spam 82 3. >>> spam = spam + 2 >>> spam 42

第一次存入一个值，变量就被"初始化"（或创建）1. 。此后，可以在表达式中使用它，以及其他变量和值2. 。如果变量被赋了一个新值，老值就被忘记了3. 。这就是为什么在例子结束时，spam求值为42，而不是40。这称为"覆写"该变量。在交互式环境中输入以下代码，尝试覆写一个字符串：>>> spam = 'Hello' >>> spam 'Hello' >>> spam = 'Goodbye' >>> spam 'Goodbye'

就像图1-3中的盒子，这个例子中的spam变量保存了'Hello'，直到你用'Goodbye'替代它。

图1-3 如果一个新值赋给变量，老值就被遗忘了

### 1.4.2 变量名表1-3中有一些合法变量名的例子。你可以给变量取任何名字，只要它遵守以下3条规则：

1．只能是一个词。

2．只能包含字母、数字和下划线。

3．不能以数字开头。

表1-3 有效和无效的变量名有效的变量名无效的变量名

balance

current-balance（不允许中划线）

currentBalance

current balanc（不允许空格）

current_balance

4account（不允许数字开头）

_spam

42（不允许数字开头）

SPAM

total_$um（不允许$这样的特殊字符）

account4

'hello'（不允许'这样的特殊字符）

变量名是区分大小写的。这意味着，spam、 SPAM、Spam和sPaM是4个不同的变量。变量用小写字母开头是Python的惯例。

本书的变量名使用了驼峰形式，没有用下划线。也就是说，变量名用lookLikeThis，而不是looking_like_this。一些有经验的程序员可能会指出，官方的Python代码风格PEP 8，即应该使用下划线。我喜欢驼峰式，这没有错，并认为PEP 8本身"愚蠢的一致性是头脑狭隘人士的心魔"："一致地满足风格指南是重要的。但最重要的是，知道何时要不一致，因为有时候风格指南就是不适用。如果有怀疑，请相信自己的最佳判断。"

好的变量名描述了它包含的数据。设想你搬到一间新屋子，搬家纸箱上标的都是"东西"。你永远找不到任何东西！本书的例子和许多Python的文档，使用spam、eggs和bacon等变量名作为一般名称（受到Monty Python的"Spam"短剧的影响），但在你的程序中，具有描述性的名字有助于提高代码可读性。

## 1.5 第一个程序虽然交互式环境对于一次运行一条 Python指令很好，但要编写完整的Python程序，就需要在文件编辑器中输入指令。"文件编辑器"类似于Notepad或TextMate这样的文本编辑器，它有一些针对输入源代码的特殊功能。要在IDLE中打开文件编辑器，请选择FileNew ▶File。

出现的窗口中应该包含一个光标，等待你输入，但它与交互式环境不同。在交互式环境中，按下回车，就会执行Python指令。文件编辑器允许输入许多指令，保存为文件，并运行该程序。下面是区别这两者的方法：

- 交互式环境窗口总是有>>>提示符。

- 文件编辑器窗口没有>>>提示符。

现在是创建第一个程序的时候了！在文件编辑器窗口打开后，输入以下内容：1. # This program says hello and asks for my name. 2. print('Hello world!') print('What is your name?') # ask for their name 3. myName = input() 4. print('It is good to meet you, ' + myName) 5. print('The length of your name is:') print(len(myName)) 6. print('What is your age?') # ask for their age myAge = input() print('You will be ' + str(int(myAge) + 1) + ' in a year.')

在输入完源代码后保存它，这样就不必在每次启动IDLE时重新输入。从文件编辑器窗口顶部的菜单，选择File▶Save As。在"Save As"窗口中，在输入框输入hello.py，然后点击"Save"。

在输入程序时，应该过一段时间就保存你的程序。这样，如果计算机崩溃，或者不小心退出了IDLE，也不会丢失代码。作为快捷键，可以在Windows和Linux上按Ctrl-S，在OS X上按⌘-S，来保存文件。

在保存文件后，让我们来运行程序。选择Run▶Run Module，或按下F5键。程序将在交互式环境窗口中运行，该窗口是首次启动IDLE时出现的。记住，必须在文件编辑器窗口中按F5，而不是在交互式环境窗口中。在程序要求输入时，输入你的名字。在交互式环境中，程序输出应该看起来像这样：Python 3.3.2 (v3.3.2:d047928ae3f6, May 16 2013, 00:06:53) [MSC v.1600 64 bit (AMD64)] on win32 Type "copyright", "credits" or "license()" for more information. >>> ================================ RESTART ================================ >>> Hello world! What is your name? Al It is good to meet you, Al The length of your name is: 2 What is your age? 4 You will be 5 in a year. >>>

如果没有更多代码行要执行，Python程序就会"中止"。也就是说，它停止运行。（也可以说Python程序"退出"了。）

可以通过点击窗口上部的X，关闭文件编辑器。要重新加载一个保存了的程序，就在菜单中选择File▶Open。现在请这样做，在出现的窗口中选择hello.py，并点击"Open"按钮。前面保存的程序hello.py应该在文件编辑器窗口中打开。

## 1.6 程序剖析新程序在文件编辑器中打开后，让我们快速看一看它用到的Python指令，逐一查看每行代码。

### 1.6.1 注释下面这行称为"注释"。1. # This program says hello and asks for my name.

Python会忽略注释，你可以用它们来写程序注解，或提醒自己代码试图完成的事。这一行中，#标志之后的所有文本都是注释。

有时候，程序员在测试代码时，会在一行代码前面加上#，临时删除它。这称为"注释掉"代码。在你想搞清楚为什么程序不工作时，这样做可能有用。稍后，如果你准备还原这一行代码，可以去掉#。

Python也会忽略注释之后的空行。在程序中，想加入空行时就可以加入。这会让你的代码更容易阅读，就像书中的段落一样。

### 1.6.2 print()函数

print()函数将括号内的字符串显示在屏幕上。2. print('Hello world!') print('What is your name?') # ask for their name

代码行print('Hello world!')表示"打印出字符串'Hello world!'的文本"。Python执行到这行时，你告诉Python调用print()函数，并将字符串"传递"给函数。传递给函数的值称为"参数"。请注意，引号没有打印在屏幕上。它们只是表示字符串的起止，不是字符串的一部分。

也可以用这个函数在屏幕上打印出空行，只要调用print()就可以了，括号内没有任何东西。

在写函数名时，末尾的左右括号表明它是一个函数的名字。这就是为什么在本书中你会看到print()，而不是print。第2章更详细地探讨了函数。

### 1.6.3 input()函数函数等待用户在键盘上输入一些文本，并按下回车键。3. myName = input()

这个函数求值为一个字符串，即用户输入的文本。前面的代码行将这个字符串赋给变量myName。

你可以认为input()函数调用是一个表达式，它求值为用户输入的任何字符串。如果用户输入'Al'，那么该表达式就求值为myName = 'Al'。

### 1.6.4 打印用户的名字接下来的print()调用，在括号间包含表达式'It is good to meet you, ' + myName。4. print('It is good to meet you, ' + myName)

要记住，表达式总是可以求值为一个值。如果'Al'是上一行代码保存在myName中的值，那么这个表达式就求值为'It is good to meet you, Al'。这个字符串传给print()，它将输出到屏幕上。

### 1.6.5 len()函数你可以向len()函数传递一个字符串（或包含字符串的变量），然后该函数求值为一个整型值，即字符串中字符的个数。5. print('The length of your name is:') print(len(myName))

在交互式环境中输入以下内容试一试：>>> len('hello') 5 >>> len('My very energetic monster just scarfed nachos.') 46 >>> len('') 0

就像这些例子，len(myName)求值为一个整数。然后它被传递给print()，在屏幕上显示。请注意，print()允许传入一个整型值或字符串。但如果在交互式环境中输入以下内容，就会报错： >>> print('I am ' + 29 + ' years old.') Traceback (most recent call last): File "<pyshell#6>", line 1, in <module> print('I am ' + 29 + ' years old.') TypeError: Can't convert 'int' object to str implicitly

导致错误的原因不是print()函数，而是你试图传递给print()的表达式。如果在交互式环境中单独输入这个表达式，也会得到同样的错误。>>> 'I am ' + 29 + ' years old.' Traceback (most recent call last): File "<pyshell#7>", line 1, in <module> 'I am ' + 29 + ' years old.' TypeError: Can't convert 'int' object to str implicitly

报错是因为，只能用+操作符加两个整数，或连接两个字符串。不能让一个整数和一个字符串相加，因为这不符合Python的语法。可以使用字符串版本的整数，修复这个错误。这在下一节中解释。

### 1.6.6 str()、int()和float()函数如果想要连接一个整数（如29）和一个字符串，再传递给print()，就需要获得值'29'。它是29的字符串形式。str()函数可以传入一个整型值，并求值为它的字符串形式，像下面这样：>>> str(29) '29' >>> print('I am ' + str(29) + ' years old.') I am 29 years old.

因为str(29)求值为'29'，所以表达式'I am ' + str(29) + ' years old.'求值为'I am ' + '29' + ' years old.'，它又求值为'I am 29 years old.'。这就是传递给print()函数的值。

str()、int()和float()函数将分别求值为传入值的字符串、整数和浮点数形式。请尝试用这些函数在交互式环境中转换一些值，看看会发生什么。>>> str(0) '0' >>> str(-3.14) '-3.14' >>> int('42') 42 >>> int('-99') -99 >>> int(1.25) 1 >>> int(1.99) 1 >>> float('3.14') 3.14 >>> float(10) 10.0

前面的例子调用了str()、int()和float()函数，向它们传入其他数据类型的值，得到了字符串、整型或浮点型的值。

如果想要将一个整数或浮点数与一个字符串连接，str()函数就很方便。如果你有一些字符串值，希望将它们用于数学运算，int()函数也很有用。例如，input()函数总是返回一个字符串，即便用户输入的是一个数字。在交互式环境中输入spam = input()，在它等待文本时输入101。>>> spam = input() 101 >>> spam '101'

保存在spam中的值不是整数101，而是字符串'101'。如果想要用spam中的值进行数学运算，那就用int()函数取得spam的整数形式，然后将这个新值存在spam中。>>> spam = int(spam) >>> spam 101

现在你应该能将spam变量作为整数，而不是字符串使用。>>> spam * 10 / 5 202.0

请注意，如果你将一个不能求值为整数的值传递给int()，Python将显示出错信息。>>> int('99.99') Traceback (most recent call last): File "<pyshell#18>", line 1, in <module> int('99.99') ValueError: invalid literal for int() with base 10: '99.99' >>> int('twelve') Traceback (most recent call last): File "<pyshell#19>", line 1, in <module> int('twelve') ValueError: invalid literal for int() with base 10: 'twelve'

如果需要对浮点数进行取整运算，也可以用int()函数。>>> int(7.7) 7 >>> int(7.7) + 1 8

在你的程序中，最后3行使用了函数int()和str()，取得适当数据类型的值。6. print('What is your age?') # ask for their age myAge = input() print('You will be ' + str(int(myAge) + 1) + ' in a year.')

myAge变量包含了input()函数返回的值。因为input()函数总是返回一个字符串（即使用户输入的是数字），所以你可以使用int(myAge)返回字符串的整型值。这个整型值随后在表达式int(myAge) + 1中与1相加。

相加的结果传递给str()函数：str(int(myAge) + 1)。然后，返回的字符串与字符串'You will be '和' in a year.'连接，求值为一个更长的字符串。这个更长的字符串最终传递给print()，在屏幕上显示。

假定用户输入字符串'4'，保存在myAge中。字符串'4'被转换为一个整型，所以你可以对它加1。结果是5。str()函数将这个结果转化为字符串，这样你就可以将它与第二个字符串'in a year.'连接，创建最终的消息。这些求值步骤如图1-4所示。

文本和数字相等判断虽然数字的字符串值被认为与整型值和浮点型值完全不同，但整型值可以与浮点值相等。>>> 42 == '42' False >>> 42 == 42.0 True >>> 42.0 == 0042.000 True

Python进行这种区分，因为字符串是文本，而整型值和浮点型都是数字。

图1-4 如果4保存在myAge中，求值的步骤

## 1.7 小结你可以用一个计算器来计算表达式，或在文本处理器中输入字符串连接。甚至可以通过复制粘贴文本，很容易地实现字符串复制。但是表达式以及组成它们的值（操作符、变量和函数调用），才是构成程序的基本构建块。一旦你知道如何处理这些元素，就能够用Python操作大量的数据。

最好是记住本章中介绍的不同类型的操作符（+、-、­*­、/、//、%和­**­是数学操作符，+和­*­是字符串操作符），以及3种数据类型（整型、浮点型和字符串）。

我们还介绍了几个不同的函数。print()和input()函数处理简单的文本输出（到屏幕）和输入（通过键盘）。len()函数接受一个字符串，并求值为该字符串中字符的数目。

在下一章中，你将学习如何告诉Python根据它拥有的值，明智地决定什么代码要运行，什么代码要跳过，什么代码要重复。这称为"控制流"，它让你编写程序来做出明智的决定。

## 1.8 习题

1．下面哪些是操作符，哪些是值？* 'hello' -88.8 - / + 5

2．下面哪个是变量，哪个是字符串？spam 'spam'

3．说出3种数据类型。

4．表达式由什么构成？所有表达式都做什么事？

5．本章介绍了赋值语句，如spam = 10。表达式和语句有什么区别？

6．下列语句运行后，变量bacon的值是什么？bacon = 20 bacon + 1

7．下面两个表达式求值的结果是什么？'spam' + 'spamspam' 'spam' * 3

8．为什么eggs是有效的变量名，而100是无效的？

9．哪3个函数能分别取得一个值的整型、浮点型或字符串版本？

10．为什么这个表达式会导致错误？如何修复？'I have eaten ' + 99 + ' burritos.'

附加题：在线查找len()函数的Python文档。它在一个标题为"Built-in Functions"的网页上。扫一眼Python的其他函数的列表，查看round()函数的功能，在交互式环境中使用它。

# 第2章控制流你已经知道了单条指令的基本知识。程序就是一系列指令。但编程真正的力量不仅在于运行（或"执行"）一条接一条的指令，就像周末的任务清单那样。根据表达式求值的结果，程序可以决定跳过指令，重复指令，或从几条指令中选择一条运行。实际上，你几乎永远不希望程序从第一行代码开始，简单地执行每行代码，直到最后一行。"控制流语句"可以决定在什么条件下执行哪些Python语句。

这些控制流语句直接对应于流程图中的符号，所以在本章中，我将提供示例代码的流程图。图2-1展示了一张流程图，内容是如果下雨怎么办。按照箭头构成的路径，从开始到结束。

在流程图中，通常有不止一种方法从开始走到结束。计算机程序中的代码行也是这样。流程图用菱形表示这些分支节点，其他步骤用矩形表示。开始和结束步骤用带圆角的矩形表示。

但在学习流程控制语句之前，首先要学习如何表示这些yes和no选项。同时你也需要理解，如何将这些分支节点写成Python代码。要做到这一点，让我们先看看布尔值、比较操作符和布尔操作符。

图2-1 一张流程图，告诉你如果下雨要做什么

## 2.1 布尔值虽然整型、浮点型和字符串数据类型有无数种可能的值，但"布尔"数据类型只有两种值：True和False。Boolean（布尔）的首字母大写，因为这个数据类型是根据数学家George Boole命名的。在作为Python代码输入时，布尔值True和False不像字符串，两边没有引号，它们总是以大写字母T或F开头，后面的字母小写。在交互式环境中输入下面内容，其中有些指令是故意弄错的，它们将导致出错信息。1. >>> spam = True >>> spam True 2. >>> true Traceback (most recent call last): File "<pyshell#2>", line 1, in <module> true NameError: name 'true' is not defined 3. >>> True = 2 + 2 SyntaxError: assignment to keyword

像其他值一样，布尔值也用在表达式中，并且可以保存在变量中1. 。如果大小写不正确2. ，或者试图使用True和False作为变量名3. ，Python就会给出错误信息。

## 2.2 比较操作符

"比较操作符"比较两个值，求值为一个布尔值。表2-1列出了比较操作符。

表2-1 比较操作符操作符含义

==

等于

!=

不等于

<

小于

>

大于

<=

小于等于

>=

大于等于这些操作符根据给它们提供的值，求值为True或False。现在让我们尝试一些操作符，从==和!=开始。>>> 42 == 42 True >>> 42 == 99 False >>> 2 != 3 True >>> 2 != 2 False

如果两边的值一样，==（等于）求值为True。如果两边的值不同，!=（不等于）求值为False。==和!=操作符实际上可以用于所有数据类型的值。 >>> 'hello' == 'hello' True >>> 'hello' == 'Hello' False >>> 'dog' != 'cat' True >>> True == True True >>> True != False True >>> 42 == 42.0 True 1. >>> 42 == '42' False

请注意，整型或浮点型的值永远不会与字符串相等。表达式42 == '42'1. 求值为False是因为，Python认为整数42与字符串'42'不同。

另一方面，<、>、<=和>=操作符仅用于整型和浮点型值。 >>> 42 < 100 True >>> 42 > 100 False >>> 42 < 42 False >>> eggCount = 42 2. >>> eggCount <= 42 True >>> myAge = 29 3. >>> myAge >= 10 True

操作符的区别你可能已经注意到，==操作符（等于）有两个等号，而=操作符（赋值）只有一个等号。这两个操作符很容易混淆。只要记住：
-

==操作符（等于）问两个值是否彼此相同。
-

=操作符（赋值）将右边的值放到左边的变量中。

为了记住谁是谁，请注意==操作符（等于）包含两个字符，就像!=操作符（不等于）包含两个字符一样。

你会经常用比较操作符比较一个变量和另外某个值。就像在例子eggCount <= 421. 和myAge >= 102. 中一样（毕竟，除了在代码中输入'dog' != 'cat'以外，你本来也可以直接输入True）。稍后，在学习控制流语句时，你会看到更多的例子。

## 2.3 布尔操作符

3个布尔操作符（and、or和not）用于比较布尔值。像比较操作符一样，它们将这些表达式求值为一个布尔值。让我们仔细看看这些操作符，从and操作符开始。

### 2.3.1 二元布尔操作符

and和or操作符总是接受两个布尔值（或表达式），所以它们被认为是"二元"操作符。如果两个布尔值都为True，and操作符就将表达式求值为True，否则求值为False。在交互式环境中输入某个使用and的表达式，看看效果。>>> True and True True >>> True and False False

"真值表"显示了布尔操作符的所有可能结果。表2-2是操作符and的真值表。

表2-2 and操作符的真值表表达式求值为

True and True

True

True and False

False

False and True

False

False and False

False

另一方面，只要有一个布尔值为真，or操作符就将表达式求值为True。如果都是False，所求值为False。>>> False or True True >>> False or False False

可以在or操作符的真值表中看到每一种可能的结果，如表2-3所示。

表2-3 or操作符的真值表表达式求值为

True or True

True

True or False

True

False or True

True

False or False

False

### 2.3.2 not操作符和and和or不同，not操作符只作用于一个布尔值（或表达式）。not操作符求值为相反的布尔值。 >>> not True False 1. >>> not not not not True True

就像在说话和写作中使用双重否定，你可以嵌套not操作符1. ，虽然在真正的程序中并不经常这样做。表2-4展示了not的真值表。

表2-4 not操作符的真值表表达式求值为

not True

False

not False

True

## 2.4 混合布尔和比较操作符既然比较操作符求值为布尔值，就可以和布尔操作符一起，在表达式中使用。

回忆一下，and、or和not操作符称为布尔操作符是因为，它们总是操作于布尔值。虽然像4 < 5这样的表达式不是布尔值，但可以求值为布尔值。在交互式环境中，尝试输入一些使用比较操作符的布尔表达式。>>> (4 < 5) and (5 < 6) True >>> (4 < 5) and (9 < 6) False >>> (1 == 2) or (2 == 2) True

计算机将先求值左边的表达式，然后再求值右边的表达式。知道两个布尔值后，它又将整个表达式再求值为一个布尔值。你可以认为计算机求值(4 < 5)和(5 < 6)的过程，如图2-2所示。

图2-2 (4 < 5)和 (5 < 6) 求值为True的过程也可以在一个表达式中使用多个布尔操作符，与比较操作符一起使用。>>> 2 + 2 == 4 and not 2 + 2 == 5 and 2 * 2 == 2 + 2 True

和算术操作符一样，布尔操作符也有操作顺序。在所有算术和比较操作符求值后，Python先求值not操作符，然后是and操作符，然后是or操作符。

## 2.5 控制流的元素控制流语句的开始部分通常是"条件"，接下来是一个代码块，称为"子句"。在开始学习具体的Python控制流语句之前，我将介绍条件和代码块。

### 2.5.1 条件你前面看到的布尔表达式可以看成是条件，它和表达式是一回事。"条件"只是在控制流语句的上下文中更具体的名称。条件总是求值为一个布尔值，True或False。控制流语句根据条件是True还是False，来决定做什么。几乎所有的控制流语句都使用条件。

### 2.5.2 代码块一些代码行可以作为一组，放在"代码块"中。可以根据代码行的缩进，知道代码块的开始和结束。代码块有3条规则。

1．缩进增加时，代码块开始。

2．代码块可以包含其他代码块。

3．缩进减少为零，或减少为外面包围代码块的缩进，代码块就结束了。

看一些有缩进的代码，更容易理解代码块。所以让我们在一小段游戏程序中，寻找代码块，如下所示： if name == 'Mary': 1. print('Hello Mary') if password == 'swordfish': 2. print('Access granted.') else: 3. print('Wrong password.')

第一个代码块1. 开始于代码行print('Hello Mary')，并且包含后面所有的行。在这个代码块中有另一个代码块2. ，它只有一行代码：print('Access Granted.')。第三个代码块3. 也只有一行：print('Wrong password.')。

## 2.6 程序执行在第1章的hello.py程序中，Python开始执行程序顶部的指令，然后一条接一条往下执行。"程序执行"（或简称"执行"）这一术语是指当前被执行的指令。如果将源代码打印在纸上，在它执行时用手指指着每一行代码，你可以认为手指就是程序执行。

但是，并非所有的程序都是从上至下简单地执行。如果用手指追踪一个带有控制流语句的程序，可能会发现手指会根据条件跳过源代码，有可能跳过整个子句。

## 2.7 控制流语句现在，让我们来看最重要的控制流部分：语句本身。语句代表了在图2-1的流程图中看到的菱形，它们是程序将做出的实际决定。

### 2.7.1 if语句最常见的控制流语句是if语句。if语句的子句（也就是紧跟if语句的语句块），将在语句的条件为True时执行。如果条件为False，子句将跳过。

在英文中，if语句念起来可能是："如果条件为真，执行子句中的代码。"在Python中，if语句包含以下部分：

- if关键字；

- 条件（即求值为True或False的表达式）；

- 冒号；

- 在下一行开始，缩进的代码块（称为if子句）。

例如，假定有一些代码，检查某人的名字是否为Alice（假设此前曾为name赋值）。if name == 'Alice': print('Hi, Alice.')

所有控制流语句都以冒号结尾，后面跟着一个新的代码块（子句）。语句的if子句是代码块，包含print('Hi, Alice.')。图2-3展示了这段代码的流程图。

图2-3 if语句的流程图

### 2.7.2 else语句

if子句后面有时候也可以跟着else语句。只有if语句的条件为False时，else子句才会执行。在英语中，else语句读起来可能是："如果条件为真，执行这段代码。否则，执行那段代码"。else语句不包含条件，在代码中，else语句中包含下面部分：

- else关键字；

- 冒号；

- 在下一行开始，缩进的代码块（称为else子句）。

回到Alice的例子，我们来看看使用else语句的一些代码，在名字不是Alice时，提供不一样的问候。if name == 'Alice': print('Hi, Alice.') else: print('Hello, stranger.')

图2-4展示了这段代码的流程图。

图2-4 else语句的流程图

### 2.7.3 elif语句虽然只有if或else子句会被执行，但有时候可能你希望，"许多"可能的子句中有一个被执行。elif语句是"否则如果"，总是跟在if或另一条elif语句后面。它提供了另一个条件，仅在前面的条件为False时才检查该条件。在代码中，elif语句总是包含以下部分：

- elif关键字；

- 条件（即求值为True或False的表达式）；

- 冒号；

- 在下一行开始，缩进的代码块（称为elif子句）。

让我们在名字检查程序中添加elif，看看这个语句的效果。if name == 'Alice': print('Hi, Alice.') elif age < 12: print('You are not Alice, kiddo.')

这一次，检查此人的年龄。如果比 12 岁小，就告诉他一些不同的东西。可以在图2-5中看到这段代码的流程图。

如果age < 12为True并且name == 'Alice'为False，elif子句就会执行。但是，如果两个条件都为False，那么两个子句都会跳过。"不能"保证至少有一个子句会被执行。如果有一系列的elif语句，仅有一条或零条子句会被执行。一旦一个语句的条件为True，剩下的elif子句会自动跳过。例如，打开一个新的文件编辑器窗口，输入以下代码，保存为vampire.py。if name == 'Alice': print('Hi, Alice.') elif age < 12: print('You are not Alice, kiddo.') elif age > 2000: print('Unlike you, Alice is not an undead, immortal vampire.') elif age > 100: print('You are not Alice, grannie.')

图2-5 elif语句的流程图这里，我添加了另外两条elif语句，让名字检查程序根据age的不同答案而发出问候。图2-6展示了这段代码的流程图。

但是，elif语句的次序确实重要。让我们重新排序，引入一个缺陷。回忆一下，一旦找到一个True条件，剩余的子句就会自动跳过。所以如果交换vampire.py中的一些子句，就会遇到问题。像下面这样改变代码，将它保存为vampire2.py。 if name == 'Alice': print('Hi, Alice.') elif age < 12: print('You are not Alice, kiddo.') 1. elif age > 100: print('You are not Alice, grannie.') elif age > 2000: print('Unlike you, Alice is not an undead, immortal vampire.')

图2-6 vampire.py程序中多重elif语句的流程图假设在这段代码执行之前，age变量的值是3000。你可能预计代码会打印出字符串'Unlike you, Alice is not an undead, immortal vampire.'。但是，因为age > 100条件为真（毕竟3000大于100）1. ，字符串'You are not Alice, grannie.'被打印出来，剩下的语句自动跳过。别忘了，最多只有一个子句会执行，对于elif语句，次序是很重要的。

图2-7展示了前面代码的流程图。请注意，菱形age > 100和age > 2000交换了位置。

图2-7 vampire2.py程序的流程图。打叉的路径在逻辑上永远不会发生， 因为如果age大于2000，它就已经大于100了你可以选择在最后的elif语句后面加上else语句。在这种情况下，保证至少一个子句（且只有一个）会执行。如果每个if和elif语句中的条件都为False，就执行else子句。例如，让我们使用if、elif和else子句重新编写Alicee程序。if name == 'Alice': print('Hi, Alice.') elif age < 12: print('You are not Alice, kiddo.') else: print('You are neither Alice nor a little kid.')

图2-8展示了这段新代码的流程图，我们将它保存为littleKid.py。

图2-8 前面littleKid.py程序的流程图在英语中，这类控制流结构会使得："如果第一个条件为真，做这个。否则，如果第二个条件为真，做那个。否则，做另外的事。"如果你同时使用这3个语句，要记住这些次序规则，避免图2-7中那样的缺陷。首先，总是只有一个if语句。所有需要的elif语句都应该跟在if语句之后。其次，如果希望确保至少一条子句被执行，在最后加上else语句。

### 2.7.4 while循环语句利用while语句，可以让一个代码块一遍又一遍的执行。只要while语句的条件为True，while子句中的代码就会执行。在代码中，while语句总是包含下面几部分：

- 关键字；

- 条件（求值为True或False的表达式）；

- 冒号；

- 从新行开始，缩进的代码块（称为while子句）。

可以看到，while语句看起来和if语句类似。不同之处是它们的行为。if子句结束时，程序继续执行if语句之后的语句。但在while子句结束时，程序执行跳回到while语句开始处。while子句常被称为"while循环"，或就是"循环"。

让我们来看一个if语句和一个while循环。它们使用同样的条件，并基于该条件做出同样的动作。下面是if语句的代码：spam = 0 if spam < 5: print('Hello, world.') spam = spam + 1

下面是while语句的代码：spam = 0 while spam < 5: print('Hello, world.') spam = spam + 1

这些语句类似，if和while都检查spam的值，如果它小于５，就打印一条消息。但如果运行这两段代码，它们各自的表现非常不同。对于if语句，输出就是"Hello, world."。但对于while语句，输出是"Hello, world."重复了5次！看一看这两段代码的流程图，图2-9和2-10，找一找原因。

图2-9 if语句代码的流程图图2-10 while语句代码的流程图带有if语句的代码检查条件，如果条件为True，就打印一次"Hello, world."。带有while循环的代码则不同，会打印5次。打印5次后停下来是因为，在每次循环迭代末尾，spam中的整数都增加1。这意味着循环将执行5次，然后spam < 5变为False。

在while循环中，条件总是在每次"迭代"开始时检查（也就是每次循环执行时）。如果条件为True，子句就会执行，然后，再次检查条件。当条件第一次为False时，while子句就跳过。

### 2.7.5 恼人的循环这里有一个小例子，它不停地要求你输入"your name"（就是这个字符串，而不是你的名字）。选择FileNew Window，打开一个新的文件编辑器窗口，输入以下代码，将文件保存为yourName.py：1. name = '' 2. while name != 'your name': print('Please type your name.') 3. name = input() 4. print('Thank you!')

首先，程序将变量name1. 设置为一个空字符串。这样，条件name != 'your name'就会求值为True，程序就会进入while循环的子句2. 。

这个子句内的代码要求用户输入他们的名字，然后赋给name变量3. 。因为这是语句块的最后一行，所以执行就回到while循环的开始，重新对条件求值。如果name中的值"不等于"字符串'your name'，那么条件就为True，执行将再次进入while子句。

但如果用户输入your name，while循环的条件就变成'your name' != 'your name'，它求值为False。条件现在是False，程序就不会再次进入while循环子句，而是跳过它，继续执行程序后面的部分4. 。图2-11展示了yourName.py程序的流程图。

图2-11 yourName.py程序的流程图现在，让我们来看看yourName.py程序的效果。按F5键运行它，输几次your name之外的东西，然后再提供程序想要的输入。Please type your name. Al Please type your name. Albert Please type your name. %#@#%*(^&!!! Please type your name. your name Thank you!

如果永不输入your name，那么循环的条件就永远不会为False，程序将永远问下去。这里，input()调用让用户输入正确的字符串，以便让程序继续。在其他程序，条件可能永远没有实际变化，这可能会出问题。让我们来看看如何跳出循环。

### 2.7.6 break语句有一个捷径，让执行提前跳出while循环子句。如果执行遇到break语句，就会马上退出while循环子句。在代码中，break语句仅包含break关键字。

非常简单，对吗？这里有一个程序，和前面的程序做一样的事情，但使用了break语句来跳出循环。输入以下代码，将文件保存为yourName2.py：1. while True: print('Please type your name.') 2. name = input() 3. if name == 'your name': 4. break 5. print('Thank you!')

第一行1. 创建了一个"无限循环"，它是一个条件总是为True的while循环。（表达式True总是求值为True。）程序执行将总是进入循环，只有遇到break语句执行时才会退出（"永远不"退出的无限循环是一个常见的编程缺陷）。

像以前一样，程序要求用户输入your name2. 。但是现在，虽然执行仍然在while循环内，但有一个if语句会被执行3. ，检查name是否等于your name。如果条件为True，break语句就会运行4. ，执行就会跳出循环，转到print('Thank you!') 5. 。否则，包含break语句的if语句子句就会跳过，让执行到达while循环的末尾。此时，程序执行跳回到while语句的开始1. ，重新检查条件。因为条件是True，所以执行进入循环，再次要求用户输入your name。这个程序的流程图参见图2-12。

运行yourName2.py，输入你为yourName.py程序输入的同样文本。重写的程序应该和原来的程序反应相同。

图2-12 带有无限循环的程序的流程图。注意打叉路径在逻辑上永远不会发生，因为循环条件总是为True

### 2.7.7 continue语句像break语句一样，continue语句用于循环内部。如果程序执行遇到continue语句，就会马上跳回到循环开始处，重新对循环条件求值（这也是执行到达循环末尾时发生的事情）。

让我们用continue写一个程序，要求输入名字和口令。在一个新的文件编辑窗口中输入以下代码，将程序保存为swordfish.py。 while True: print('Who are you?') name = input() 1. if name != 'Joe': 2. continue print('Hello, Joe. What is the password? (It is a fish.)') 3. password = input() if password == 'swordfish': 4. break 5. print('Access granted.')

如果用户输入的名字不是Joe1. ，continue语句2. 将导致程序执行跳回到循环开始处。再次对条件求值时，执行总是进入循环，因为条件就是True。如果执行通过了if语句，用户就被要求输入口令3. 。如果输入的口令是swordfish，break语句运行4. ，执行跳出while循环，打印Access granted5. 。否则，执行继续到while循环的末尾，又跳回到循环的开始。这个程序的流程图参见图2-13。

陷在无限循环中？

如果你运行一个有缺陷的程序，导致陷在一个无限循环中，那么请按Ctrl-C。这将向程序发送KeyboardInterrupt错误，导致它立即停止。试一下，在文件编辑器中创建一个简单的无限循环，将它保存为infiniteloop.py。while True: print('Hello world!')

如果运行这个程序，它将永远在屏幕上打印Hello world！因为while语句的条件总是True。在IDLE的交互式环境窗口中，只有两种办法停止这个程序：按下Ctrl-C或从菜单中选择ShellRestart Shell。如果你希望马上停止程序，即使它不是陷在一个无限循环中，Ctrl-C也是很方便的。

运行这个程序，提供一些输入。只有你声称是Joe，它才会要求输入口令。一旦输入了正确的口令，它就会退出。Who are you? I'm fine, thanks. Who are you? Who are you? Joe Hello, Joe. What is the password? (It is a fish.) Mary Who are you? Joe Hello, Joe. What is the password? (It is a fish.) swordfish Access granted.

图2-13 swordfish.py的流程图。打叉的路径在逻辑上永远不会执行，因为循环条件总是True

### 2.7.8 for循环和range()函数在条件为True时，while循环就会继续循环（这是它的名称的由来）。但如果你想让一个代码块执行固定次数，该怎么办？可以通过for循环语句和range()函数来实现。

"类真"和"类假"的值其他数据类型中的某些值，条件认为它们等价于True和False。在用于条件时，0、0.0和' '（空字符串）被认为是False，其他值被认为是True。例如，请看下面的程序：name = '' while not name:1. print('Enter your name:') name = input() print('How many guests will you have?') numOfGuests = int(input()) if numOfGuests:2. print('Be sure to have enough room for all your guests.')3. print('Done')

如果用户输入一个空字符串给name，那么while语句的条件就会是True 1. ，程序继续要求输入名字。如果numOfGuests不是0 2. ，那么条件就被认为是True，程序就会为用户打印一条提醒信息3. 。

可以用not name != ' '代替not name，用numOfGuests != 0代替numOfGuests，但使用类真和类假的值会让代码更容易阅读。

在代码中，for语句看起来像for i in range(5):这样，总是包含以下部分：

- for关键字；

- 一个变量名；

- in关键字；

- 调用range()方法，最多传入3个参数；

- 冒号；

- 从下一行开始，缩进的代码块（称为for子句）。

让我们创建一个新的程序，名为fiveTimes.py，看看for循环的效果。print('My name is') for i in range(5): print('Jimmy Five Times (' + str(i) + ')')

for循环子句中的代码运行了5次。第一次运行时，变量i被设为0。子句中的print()调用将打印出Jimmy Five Times (0)。Python完成for循环子句内所有代码的一次迭代之后，执行将回到循环的顶部，for语句让i增加1。这就是为什么range(5)导致子句的5次迭代，i分别被设置为0、1、2、3、4。变量i将递增到（但不包括）传递给range()函数的整数。图2-14展示了fiveTimes.py程序的流程图。

图2-14 fiveTimes.py的流程图运行这个程序时，它将打印5次Jimmy Five Times和i的值，然后离开for循环。My name is Jimmy Five Times (0) Jimmy Five Times (1) Jimmy Five Times (2) Jimmy Five Times (3) Jimmy Five Times (4)

也可以在循环中使用continue语句。continue语句将让for循环变量继续下一个值，就像程序执行已经到达循环的末尾并返回开始一样。实际上，只能在while和for循环内部使用continue和break语句。如果试图在别处使用这些语句，Python将报错。

作为for循环的另一个例子，请考虑数学家高斯的故事。当高斯还是一个小孩时，老师想给全班同学布置很多计算作业。老师让他们从0加到100。高斯想到了一个聪明办法，在几秒钟内算出了答案，但你可以用for循环写一个Python程序，替你完成计算。1. total = 0 2. for num in range(101): 3. total = total + num 4. print(total)

结果应该是5050。程序刚开始时，total变量被设为0。然后for循环执行100次total = total + num。当循环完成100次迭代时，0到100的每个整数都加给了total。这时，total被打印到屏幕上。即使在最慢的计算机上，这个程序也不用1秒钟就能完成计算。

（小高斯想到，有50对数加起来是100：1 + 99, 2 + 98, 3 + 97……直到49 + 51。因为50 × 100 是5000，再加上中间的50，所以0到100的所有数之和是5050。聪明的孩子！）

### 2.7.9 等价的while循环实际上可以用while循环来做和for循环同样的事，for循环只是更简洁。让我们用与for循环等价的while循环，重写fiveTimes.py。print('My name is') i = 0 while i < 5: print('Jimmy Five Times (' + str(i) + ')') i = i + 1

运行这个程序，输出应该和使用for循环的fiveTimes.py程序一样。

### 2.7.10 range()的开始、停止和步长参数某些函数可以用多个参数调用，参数之间用逗号分开，range()就是其中之一。这让你能够改变传递给range()的整数，实现各种整数序列，包括从0以外的值开始。for i in range(12, 16): print(i)

第一个参数是for循环变量开始的值，第二个参数是上限，但不包含它，也就是循环停止的数字。12 13 14 15

range()函数也可以有第三个参数。前两个参数分别是起始值和终止值，第三个参数是"步长"。步长是每次迭代后循环变量增加的值。for i in range(0, 10, 2): print(i)

所以调用range(0, 10, 2)将从0数到8，间隔为2。0 2 4 6 8

在为for循环生成序列数据方面，range()函数很灵活。举例来说，甚至可以用负数作为步长参数，让循环计数逐渐减少，而不是增加。for i in range(5, -1, -1): print(i)

运行一个for循环，用range(5, -1, -1)来打印i，结果将从5降至0。5 4 3 2 1 0

## 2.8 导入模块

Python程序可以调用一组基本的函数，这称为"内建函数"，包括你见到过的print()、input()和len()函数。Python也包括一组模块，称为"标准库"。每个模块都是一个Python程序，包含一组相关的函数，可以嵌入你的程序之中。例如，math模块有数学运算相关的函数，random模块有随机数相关的函数，等等。

在开始使用一个模块中的函数之前，必须用import语句导入该模块。在代码中，import语句包含以下部分：

- import关键字；

- 模块的名称；

- 可选的更多模块名称，之间用逗号隔开。

在导入一个模块后，就可以使用该模块中所有很酷的函数。让我们试一试random模块，它让我们能使用random.randint()函数。

在文件编辑器中输入以下代码，保存为printRandom.py：import random for i in range(5): print(random.randint(1, 10))

如果运行这个程序，输出看起来可能像这样：4 1 8 4 1

random.randint()函数调用求值为传递给它的两个整数之间的一个随机整数。因为randint()属于random模块，必须在函数名称之前先加上random.，告诉python在random模块中寻找这个函数。

下面是import语句的例子，它导入了4个不同的模块：import random, sys, os, math

现在我们可以使用这4个模块中的所有函数。本书后面我们将学习更多的相关内容。

### from import语句

import语句的另一种形式包括from关键字，之后是模块名称，import关键字和一个星号，例如from random import *。

使用这种形式的import语句，调用random模块中的函数时不需要random.前缀。但是，使用完整的名称会让代码更可读，所以最好是使用普通形式的import语句。

## 2.9 用sys.exit()提前结束程序要介绍的最后一个控制流概念，是如何终止程序。当程序执行到指令的底部时，总是会终止。但是，通过调用sys.exit()函数，可以让程序终止或退出。因为这个函数在sys模块中，所以必须先导入sys，才能使用它。

打开一个新的文件编辑器窗口，输入以下代码。保存为exitExample.py：import sys while True: print('Type exit to exit.') response = input() if response == 'exit': sys.exit() print('You typed ' + response + '.')

在IDLE中运行这个程序。该程序有一个无限循环，里面没有break语句。结束该程序的唯一方式，就是用户输入exit，导致sys.exit()被调用。如果response等于exit，程序就会中止。因为response变量由input()函数赋值，所以用户必须输入exit，才能停止该程序。

## 2.10 小结通过使用求值为True或False的表达式（也称为条件），你可以编写程序来决定哪些代码执行，哪些代码跳过。可以在循环中一遍又一遍地执行代码，只要某个条件求值为True。如果需要跳出循环或回到开始处，break和continue语句很有用。

这些控制流语句让你写出非常聪明的程序。还有另一种类型的控制流，你可以通过编写自己的函数来实现。这是下一章的主题。

## 2.11 习题

1．布尔数据类型的两个值是什么？如何拼写？

2．3个布尔操作符是什么？

3．写出每个布尔操作符的真值表（也就是操作数的每种可能组合，以及操作的结果）。

4．以下表达式求值的结果是什么？(5 > 4) and (3 == 5) not (5 > 4) (5 > 4) or (3 == 5) not ((5 > 4) or (3 == 5)) (True and True) and (True == False) (not False) or (not True)

5．6个比较操作符是什么？

6．等于操作符和赋值操作符的区别是什么？

7．解释什么是条件，可以在哪里使用条件。

8．识别这段代码中的3个语句块：spam = 0 if spam == 10: print('eggs') if spam > 5: print('bacon') else: print('ham') print('spam') print('spam')

9．编写代码，如果变量spam中存放1，就打印Hello，如果变量中存放2，就打印Howdy，如果变量中存放其他值，就打印Greetings!

10．如果程序陷在一个无限循环中，你可以按什么键？

11．break和continue之间的区别是什么？

12．在for循环中，range(10)、range(0, 10)和range(0, 10, 1)之间的区别是什么？

13．编写一小段程序，利用for循环，打印出从1到10的数字。然后利用while循环，编写一个等价的程序，打印出从1到10的数字。

14．如果在名为spam的模块中，有一个名为bacon()的函数，那么在导入spam模块后，如何调用它？

附加题：在因特网上查找round()和abs()函数，弄清楚它们的作用。在交互式环境中尝试使用它们。

# 第3章函数从前面的章节中，你已经熟悉了print()、input()和len()函数。Python提供了这样一些内建函数，但你也可以编写自己的函数。"函数"就像一个程序内的小程序。

为了更好地理解函数的工作原理，让我们来创建一个函数。在文件编辑器中输入下面的程序，保存为helloFunc.py：1. def hello(): 2. print('Howdy!') print('Howdy!!!') print('Hello there.') 3. hello() hello() hello()

第一行是def语句1. ，它定义了一个名为hello()的函数。def语句之后的代码块是函数体2. 。这段代码在函数调用时执行，而不是在函数第一次定义时执行。

函数之后的hello()语句行是函数调用3. 。在代码中，函数调用就是函数名后跟上括号，也许在括号之间有一些参数。如果程序执行遇到这些调用，就会跳到函数的第一行，开始执行那里的代码。如果执行到达函数的末尾，就回到调用函数的那行，继续像以前一样向下执行代码。

因为这个程序调用了3次hello()函数，所以函数中的代码就执行了3次。在运行这个程序时，输出看起来像这样：Howdy! Howdy!!! Hello there. Howdy! Howdy!!! Hello there. Howdy! Howdy!!! Hello there.

函数的一个主要目的就是将需要多次执行的代码放在一起。如果没有函数定义，你可能每次都需要复制粘贴这些代码，程序看起来可能会像这样：print('Howdy!') print('Howdy!!!') print('Hello there.') print('Howdy!') print('Howdy!!!') print('Hello there.') print('Howdy!') print('Howdy!!!') print('Hello there.')

一般来说，我们总是希望避免复制代码，因为如果一旦决定要更新代码（比如说，发现了一个缺陷要修复），就必须记住要修改所有复制的代码。

随着你获得更多的编程经验，常常会发现自己在为代码"消除重复"，即去除一些重复或复制的代码。消除重复能够使程序更短、更易读、更容易更新。

## 3.1 def语句和参数如果调用print()或len()函数，你会传入一些值，放在括号之间，在这里称为"参数"。也可以自己定义接收参数的函数。在文件编辑器中输入这个例子，将它保存为helloFunc2.py：1. def hello(name): 2. print('Hello ' + name) 3. hello('Alice') hello('Bob')

如果运行这个程序，输出看起来像这样：Hello Alice Hello Bob

在这个程序的hello()函数定义中，有一个名为name的变元1. 。"变元"是一个变量，当函数被调用时，参数就存放在其中。hello()函数第一次被调用时，使用的参数是'Alice'3. 。程序执行进入该函数，变量name自动设为'Alice'，就是被print()语句打印出的内容2. 。

关于变元有一件特殊的事情值得注意：保存在变元中的值，在函数返回后就丢失了。例如前面的程序，如果你在hello('Bob')之后添加print(name)，程序会报NameError，因为没有名为name的变量。在函数调用hello('Bob')返回后，这个变量被销毁了，所以print(name)会引用一个不存在的变量name。

这类似于程序结束时，程序中的变量会丢弃。在本章稍后，当我们探讨函数的局部作用域时，我会进一步分析为什么会这样。

## 3.2 返回值和return语句如果调用len()函数，并向它传入像'Hello'这样的参数，函数调用就求值为整数5。这是传入的字符串的长度。一般来说，函数调用求值的结果，称为函数的"返回值"。

用def语句创建函数时，可以用return语句指定应该返回什么值。return语句包含以下部分：

- return关键字；

- 函数应该返回的值或表达式。

如果在return语句中使用了表达式，返回值就是该表达式求值的结果。例如，下面的程序定义了一个函数，它根据传入的数字参数，返回一个不同的字符串。在文件编辑器中输入以下代码，并保存为magic8Ball.py：1. import random 2. def getAnswer(answerNumber): 3. if answerNumber == 1: return 'It is certain' elif answerNumber == 2: return 'It is decidedly so' elif answerNumber == 3: return 'Yes' elif answerNumber == 4: return 'Reply hazy try again' elif answerNumber == 5: return 'Ask again later' elif answerNumber == 6: return 'Concentrate and ask again' elif answerNumber == 7: return 'My reply is no' elif answerNumber == 8: return 'Outlook not so good' elif answerNumber == 9: return 'Very doubtful' 4. r = random.randint(1, 9) 5. fortune = getAnswer(r) 6. print(fortune)

在这个程序开始时，Python首先导入random模块1. 。然后getAnswer()函数被定义2. 。因为函数是被定义（而不是被调用），所以执行会跳过其中的代码。接下来，random.randint()函数被调用，带两个参数，1和94. 。它求值为1和9之间的一个随机整数（包括1和9），这个值被存在一个名为r的变量中。

getAnswer()函数被调用，以r作为参数5. 。程序执行转移到getAnswer()函数的顶部3. ，r的值被保存到名为answerNumber的变元中。然后，根据answerNumber中的值，函数返回许多可能字符串中的一个。程序执行返回到程序底部的代码行，即原来调用getAnswer()的地方5. 。返回的字符串被赋给一个名为fortune变量，然后它又被传递给print()调用6. ，并被打印在屏幕上。

请注意，因为可以将返回值作为参数传递给另一个函数调用，所以你可以将下面3行代码r = random.randint(1, 9) fortune = getAnswer(r) print(fortune)

缩写成一行等价的代码：print(getAnswer(random.randint(1, 9)))

记住，表达式是值和操作符的组合。函数调用可以用在表达式中，因为它求值为它的返回值。

## 3.3 None值在Python中有一个值称为None，它表示没有值。None是NoneType数据类型的唯一值（其他编程语言可能称这个值为null、nil或undefined）。就像布尔值True和False一样，None必须大写首字母N。

如果你希望变量中存储的东西不会与一个真正的值混淆，这个没有值的值就可能有用。有一个使用None的地方就是print()的返回值。print()函数在屏幕上显示文本，但它不需要返回任何值，这和len()或input()不同。但既然所有函数调用都需要求值为一个返回值，那么print()就返回None。要看到这个效果，请在交互式环境中输入以下代码。>>> spam = print('Hello!') Hello! >>> None == spam True

在幕后，对于所有没有return语句的函数定义，Python都会在末尾加上return None。这类似于while或for循环隐式地以continue语句结尾。而且，如果使用不带值的return语句（也就是只有return关键字本身），那么就返回None。

## 3.4 关键字参数和print()

大多数参数是由它们在函数调用中的位置来识别的。例如，random.randint(1, 10)与random.randint(10, 1)不同。函数调用random.randint(1, 10)将返回1到10之间的一个随机整数，因为第一个参数是范围的下界，第二个参数是范围的上界（而random.randint(10, 1)会导致错误）。

但是，"关键字参数"是由函数调用时加在它们前面的关键字来识别的。关键字参数通常用于可选变元。例如，print()函数有可选的变元end和sep，分别指定在参数末尾打印什么，以及在参数之间打印什么来隔开它们。

如果运行以下程序：print('Hello') print('World')

输出将会是：Hello World

这两个字符串出现在独立的两行中，因为print()函数自动在传入的字符串末尾添加了换行符。但是，可以设置end关键字参数，将它变成另一个字符串。例如，如果程序像这样：print('Hello', end='') print('World')

输出就会像这样：HelloWorld

输出被打印在一行中，因为在'Hello'后面不再打印换行，而是打印了一个空字符串。如果需要禁用加到每一个print()函数调用末尾的换行，这就很有用。

类似地，如果向print()传入多个字符串值，该函数就会自动用一个空格分隔它们。在交互式环境中输入以下代码：>>> print('cats', 'dogs', 'mice') cats dogs mice

但是你可以传入sep关键字参数，替换掉默认的分隔字符串。在交互式环境中输入以下代码：>>> print('cats', 'dogs', 'mice', sep=',') cats,dogs,mice

也可以在你编写的函数中添加关键字参数，但必须先在接下来的两章中学习列表和字典数据类型。现在只要知道，某些函数有可选的关键字参数，在函数调用时可以指定。

## 3.5 局部和全局作用域在被调用函数内赋值的变元和变量，处于该函数的"局部作用域"。在所有函数之外赋值的变量，属于"全局作用域"。处于局部作用域的变量，被称为"局部变量"。处于全局作用域的变量，被称为"全局变量"。一个变量必是其中一种，不能既是局部的又是全局的。

可以将"作用域"看成是变量的容器。当作用域被销毁时，所有保存在该作用域内的变量的值就被丢弃了。只有一个全局作用域，它是在程序开始时创建的。如果程序终止，全局作用域就被销毁，它的所有变量就被丢弃了。否则，下次你运行程序的时候，这些变量就会记住它们上次运行时的值。

一个函数被调用时，就创建了一个局部作用域。在这个函数内赋值的所有变量，存在于该局部作用域内。该函数返回时，这个局部作用域就被销毁了，这些变量就丢失了。下次调用这个函数，局部变量不会记得该函数上次被调用时它们保存的值。

作用域很重要，理由如下：

- 全局作用域中的代码不能使用任何局部变量；

- 但是，局部作用域可以访问全局变量；

- 一个函数的局部作用域中的代码，不能使用其他局部作用域中的变量。

- 如果在不同的作用域中，你可以用相同的名字命名不同的变量。也就是说，可以有一个名为spam的局部变量，和一个名为spam的全局变量。

Python有不同的作用域，而不是让所有东西都成全局变量，这是有理由的。这样一来，当特定函数调用中的代码修改变量时，该函数与程序其他部分的交互，只能通过它的参数和返回值。这缩小了可能导致缺陷的代码作用域。如果程序只包含全局变量，又有一个变量赋值错误的缺陷，那就很难追踪这个赋值错误发生的位置。它可能在程序的任何地方赋值，而你的程序可能有几百到几千行！但如果缺陷是因为局部变量错误赋值，你就会知道，只有那一个函数中的代码可能产生赋值错误。

虽然在小程序中使用全局变量没有太大问题，但当程序变得越来越大时，依赖全局变量就是一个坏习惯。

### 3.5.1 局部变量不能在全局作用域内使用考虑下面的程序，它在运行时会产生错误：def spam(): eggs = 31337 spam() print(eggs)

如果运行这个程序，输出将是：Traceback (most recent call last): File "C:/test3784.py", line 4, in <module> print(eggs) NameError: name 'eggs' is not defined

发生错误是因为，eggs变量只属于spam()调用所创建的局部作用域。在程序执行从spam返回后，该局部作用域就被销毁了，不再有名为eggs的变量。所以当程序试图执行print(eggs)，Python就报错，说eggs没有定义。你想想看，这是有意义的。当程序执行在全局作用域中时，不存在局部作用域，所以不会有任何局部变量。这就是为什么只有全局变量能用于全局作用域。

### 3.5.2 局部作用域不能使用其他局部作用域内的变量一个函数被调用时，就创建了一个新的局部作用域，这包括一个函数被另一个函数调用时的情况。请看以下代码： def spam(): 1. eggs = 99 2. bacon() 3. print(eggs) def bacon(): ham = 101 4. eggs = 0 5. spam()

在程序开始运行时，spam()函数被调用5. ，创建了一个局部作用域。局部变量eggs1. 被赋值为99。然后bacon()函数被调用2. ，创建了第二个局部作用域。多个局部作用域能同时存在。在这个新的局部作用域中，局部变量ham被赋值为101。局部变量eggs（与spam()的局部作用域中的那个变量不同）也被创建4. ，并赋值为0。

当bacon()返回时，这次调用的局部作用域被销毁。程序执行在spam()函数中继续，打印出eggs的值3. 。因为spam()调用的局部作用域仍然存在，eggs变量被赋值为99。这就是程序的打印输出。

要点在于，一个函数中的局部变量完全与其他函数中的局部变量分隔开来。

### 3.5.3 全局变量可以在局部作用域中读取请看以下程序：def spam(): print(eggs) eggs = 42 spam() print(eggs)

因为在spam()函数中，没有变元名为eggs，也没有代码为eggs赋值，所以当spam()中使用eggs时，Python认为它是对全局变量eggs的引用。这就是前面的程序运行时打印出42的原因。

### 3.5.4 名称相同的局部变量和全局变量要想生活简单，就要避免局部变量与全局变量或其他局部变量同名。但在技术上，在Python中让局部变量和全局变量同名是完全合法的。为了看看实际发生的情况，请在文件编辑器中输入以下代码，并保存为sameName.py： def spam(): 1. eggs = 'spam local' print(eggs) # prints 'spam local' def bacon(): 2. eggs = 'bacon local' print(eggs) # prints 'bacon local' spam() print(eggs) # prints 'bacon local' 3. eggs = 'global' bacon() print(eggs) # prints 'global'

运行该程序，输出如下：bacon local spam local bacon local global

在这个程序中，实际上有3个不同的变量，但令人迷惑的是，它们都名为eggs。这些变量是：

1. 名为eggs的变量，存在于spam()被调用时的局部作用域；

2. 名为eggs的变量，存在于bacon()被调用时的局部作用域；

3. 名为eggs的变量，存在于全局作用域。

因为这3个独立的变量都有相同的名字，追踪某一个时刻使用的是哪个变量，可能比较麻烦。这就是应该避免在不同作用域内使用相同变量名的原因。

## 3.6 global语句如果需要在一个函数内修改全局变量，就使用global语句。如果在函数的顶部有global eggs这样的代码，它就告诉Python，"在这个函数中，eggs指的是全局变量，所以不要用这个名字创建一个局部变量。"例如，在文件编辑器中输入以下代码，并保存为sameName2.py： def spam(): 1. global eggs 2. eggs = 'spam' eggs = 'global' spam() print(eggs)

运行该程序，最后的print()调用将输出：spam

因为eggs在spam()的顶部被声明为global1. ，所以当eggs被赋值为'spam'时2. ，赋值发生在全局作用域的eggs上。没有创建局部eggs变量。

有4条法则，来区分一个变量是处于局部作用域还是全局作用域：

1．如果变量在全局作用域中使用（即在所有函数之外），它就总是全局变量。

2．如果在一个函数中，有针对该变量的global语句，它就是全局变量。

3．否则，如果该变量用于函数中的赋值语句，它就是局部变量。

4．但是，如果该变量没有用在赋值语句中，它就是全局变量。

为了更好地理解这些法则，这里有一个例子程序。在文件编辑器中输入以下代码，并保存为sameName3.py： def spam(): 1. global eggs eggs = 'spam' # this is the global def bacon(): 2. eggs = 'bacon' # this is a local def ham(): 3. print(eggs) # this is the global eggs = 42 # this is the global spam() print(eggs)

在spam()函数中，eggs是全局eggs变量，因为在函数的开始处，有针对eggs变量的global语句1. 。在bacon()中，eggs是局部变量，因为在该函数中有针对它的赋值语句2. 。在ham()中3. ，eggs是全局变量，因为在这个函数中，既没有赋值语句，也没有针对它的global语句。如果运行sameName3.py，输出将是：spam

在一个函数中，一个变量要么总是全局变量，要么总是局部变量。函数中的代码没有办法先使用名为eggs的局部变量，稍后又在同一个函数中使用全局eggs变量。

如果想在一个函数中修改全局变量中存储的值，就必须对该变量使用global语句。

在一个函数中，如果试图在局部变量赋值之前就使用它，像下面的程序这样，Python就会报错。为了看到效果，请在文件编辑器中输入以下代码，并保存为sameName4.py： def spam(): print(eggs) # ERROR! 1. eggs = 'spam local' 2. eggs = 'global' spam()

运行前面的程序，会产生出错信息。Traceback (most recent call last): File "C:/test3784.py", line 6, in <module> spam() File "C:/test3784.py", line 2, in spam print(eggs) # ERROR! UnboundLocalError: local variable 'eggs' referenced before assignment

发生这个错误是因为，Python看到spam()函数中有针对eggs的赋值语句1. ，因此认为eggs变量是局部变量。但是因为print(eggs)的执行在eggs赋值之前，局部变量eggs并不存在。Python不会退回到使用全局eggs变量2. 。

## 3.7 异常处理到目前为止，在Python程序中遇到错误，或"异常"，意味着整个程序崩溃。你不希望这发生在真实世界的程序中。相反，你希望程序能检测错误，处理它们，然后继续运行。

例如，考虑下面的程序，它有一个"除数为零"的错误。打开一个新的文件编辑器窗口，输入以下代码，并保存为zeroDivide.py：def spam(divideBy): return 42 / divideBy print(spam(2)) print(spam(12)) print(spam(0)) print(spam(1))

我们已经定义了名为spam的函数，给了它一个变元，然后打印出该函数带各种参数的值，看看会发生什么情况。下面是运行前面代码的输出：21.0 3.5 Traceback (most recent call last): File "C:/zeroDivide.py", line 6, in <module> print(spam(0)) File "C:/zeroDivide.py", line 2, in spam return 42 / divideBy ZeroDivisionError: division by zero

当试图用一个数除以零时，就会发生ZeroDivisionError。根据错误信息中给出的行号，我们知道spam()中的return语句导致了一个错误。

函数作为"黑盒"

通常，对于一个函数，你要知道的就是它的输入值（变元）和输出值。你并非总是需要加重自己的负担，弄清楚函数的代码实际是怎样工作的。如果以这种高层的方式来思考函数，通常大家会说，你将该函数看成是一个黑盒。

这个思想是现代编程的基础。本书后面的章节将向你展示一些模块，其中的函数是由其他人编写的。尽管你在好奇的时候也可以看一看源代码，但为了能使用它们，你并不需要知道它们是如何工作的。而且，因为鼓励在编写函数时不使用全局变量，你通常也不必担心函数的代码会与程序的其他部分发生交叉影响。

错误可以由try和except语句来处理。那些可能出错的语句被放在try子句中。如果错误发生，程序执行就转到接下来的except子句开始处。

可以将前面除数为零的代码放在一个try子句中，让except子句包含代码，来处理该错误发生时应该做的事。def spam(divideBy): try: return 42 / divideBy except ZeroDivisionError: print('Error: Invalid argument.') print(spam(2)) print(spam(12)) print(spam(0)) print(spam(1))

如果在try子句中的代码导致一个错误，程序执行就立即转到except子句的代码。在运行那些代码之后，执行照常继续。前面程序的输出如下：21.0 3.5 Error: Invalid argument. None 42.0

请注意，在函数调用中的try语句块中，发生的所有错误都会被捕捉。请考虑以下程序，它的做法不一样，将spam()调用放在语句块中：def spam(divideBy): return 42 / divideBy try: print(spam(2)) print(spam(12)) print(spam(0)) print(spam(1)) except ZeroDivisionError: print('Error: Invalid argument.')

该程序运行时，输出如下：21.0 3.5 Error: Invalid argument.

print(spam(1))从未被执行是因为，一旦执行跳到except子句的代码，就不会回到try子句。它会继续照常向下执行。

## 3.8 一个小程序：猜数字到目前为止，前面展示的小例子适合于介绍基本概念。现在让我们看一看，如何将所学的知识综合起来，编写一个更完整的程序。在本节中，我将展示一个简单的猜数字游戏。在运行这个程序时，输出看起来像这样：I am thinking of a number between 1 and 20. Take a guess. 10 Your guess is too low. Take a guess. 15 Your guess is too low. Take a guess. 17 Your guess is too high. Take a guess. 16 Good job! You guessed my number in 4 guesses!

在文件编辑器中输入以下代码，并保存为guessTheNumber.py：

# This is a guess the number game. import random secretNumber = random.randint(1, 20) print('I am thinking of a number between 1 and 20.') # Ask the player to guess 6 times. for guessesTaken in range(1, 7): print('Take a guess.') guess = int(input()) if guess < secretNumber: print('Your guess is too low.') elif guess > secretNumber: print('Your guess is too high.') else: break # This condition is the correct guess! if guess == secretNumber: print('Good job! You guessed my number in ' + str(guessesTaken) + ' guesses!') else: print('Nope. The number I was thinking of was ' + str(secretNumber))

让我们逐行来看看代码，从头开始。

# This is a guess the number game. import random secretNumber = random.randint(1, 20)

首先，代码顶部的一行注释解释了这个程序做什么。然后，程序导入了模块random，以便能用random.randint()函数生成一个数字，让用户来猜。返回值是一个1到20之间的随机整数，保存在变量secretNumber中。print('I am thinking of a number between 1 and 20.') # Ask the player to guess 6 times. for guessesTaken in range(1, 7): print('Take a guess.') guess = int(input())

程序告诉玩家，它有了一个秘密数字，并且给玩家6次猜测机会。在for循环中，代码让玩家输入一次猜测，并检查该猜测。该循环最多迭代6次。循环中发生的第一件事情，是让玩家输入一个猜测数字。因为input()返回一个字符串，所以它的返回值被直接传递给int()，它将字符串转变成整数。这保存在名为guess的变量中。 if guess < secretNumber: print('Your guess is too low.') elif guess > secretNumber: print('Your guess is too high.')

这几行代码检查该猜测是小于还是大于那个秘密数字。不论哪种情况，都在屏幕上打印提示。 else: break # This condition is the correct guess!

如果该猜测既不大于也不小于秘密数字，那么它就一定等于秘密数字，这时你希望程序执行跳出for循环。if guess == secretNumber: print('Good job! You guessed my number in ' + str(guessesTaken) + ' guesses!') else: print('Nope. The number I was thinking of was ' + str(secretNumber))

在for循环后，前面的if...else语句检查玩家是否正确地猜到了该数字，并将相应的信息打印在屏幕上。不论哪种情况，程序都会打印一个包含整数值的变量（guessesTaken和secretNumber）。因为必须将这些整数值连接成字符串，所以它将这些变量传递给str()函数，该函数返回这些整数值的字符串形式。现在这些字符串可以用+操作符连接起来，最后传递给print()函数调用。

## 3.9 小结函数是将代码逻辑分组的主要方式。因为函数中的变量存在于它们自己的局部作用域内，所以一个函数中的代码不能直接影响其他函数中变量的值。这限制了哪些代码才能改变变量的值，对于调试代码是很有帮助的。

函数是很好的工具，帮助你组织代码。你可以认为他们是黑盒。它们以参数的形式接收输入，以返回值的形式产生输出。它们内部的代码不会影响其他函数中的变量。

在前面几章中，一个错误就可能导致程序崩溃。在本章中，你学习了try和except语句，它们在检测到错误时会运行代码。这让程序在面对常见错误时更有灵活性。

## 3.10 习题

1．为什么在程序中加入函数会有好处？

2．函数中的代码何时执行：在函数被定义时，还是在函数被调用时？

3．什么语句创建一个函数？

4．一个函数和一次函数调用有什么区别？

5．Python程序中有多少全局作用域？有多少局部作用域？

6．当函数调用返回时，局部作用域中的变量发生了什么？

7．什么是返回值？返回值可以作为表达式的一部分吗？

8．如果函数没有返回语句，对它调用的返回值是什么？

9．如何强制函数中的一个变量指的是全局变量？

10．None的数据类型是什么？

11．import areallyourpetsnamederic语句做了什么？

12．如果在名为spam的模块中，有一个名为bacon()的函数，在引入spam后，如何调用它？

13．如何防止程序在遇到错误时崩溃？

14．try子句中发生了什么？except子句中发生了什么？

## 3.11 实践项目作为实践，请编写程序完成下列任务。

### 3.11.1 Collatz序列编写一个名为collatz()的函数，它有一个名为number的参数。如果参数是偶数，那么collatz()就打印出number // 2，并返回该值。如果number是奇数，collatz()就打印并返回3 * number + 1。

然后编写一个程序，让用户输入一个整数，并不断对这个数调用collatz()，直到函数返回值１（令人惊奇的是，这个序列对于任何整数都有效，利用这个序列，你迟早会得到1！即使数学家也不能确定为什么。你的程序在研究所谓的"Collatz序列"，它有时候被称为"最简单的、不可能的数学问题"）。

记得将input()的返回值用int()函数转成一个整数，否则它会是一个字符串。

提示如果number % 2 == 0，整数number就是偶数，如果number % 2 == 1，它就是奇数。

这个程序的输出看起来应该像这样：Enter number: 3 10 5 16 8 4 2 1

### 3.11.2 输入验证在前面的项目中添加try和except语句，检测用户是否输入了一个非整数的字符串。正常情况下，int()函数在传入一个非整数字符串时，会产生ValueError错误，比如int('puppy')。在except子句中，向用户输出一条信息，告诉他们必须输入一个整数。

# 第4章列表在你能够开始编写程序之前，还有一个主题需要理解，那就是列表数据类型及元组。列表和元组可以包含多个值，这样编写程序来处理大量数据就变得更容易。而且，由于列表本身又可以包含其他列表，所以可以用它们将数据安排成层次结构。

本章将探讨列表的基础知识。我也会讲授关于方法的内容。方法也是函数，它们与特定数据类型的值绑定。然后我会简单介绍类似列表的元组和字符串数据类型，以及它们与列表值的比较。下一章将介绍字典数据类型。

## 4.1 列表数据类型

"列表"是一个值，它包含多个字构成的序列。术语"列表值"指的是列表本身（它作为一个值，可以保存在变量中，或传递给函数，像所有其他值一样），而不是指列表值之内的那些值。列表值看起来像这样：['cat', 'bat', 'rat', 'elephant']。就像字符串值用引号来标记字符串的起止一样，列表用左方括号开始，右方括号结束，即[]。列表中的值也称为"表项"。表项用逗号分隔（就是说，它们是"逗号分隔的"）。例如，在交互式环境中输入以下代码： >>> [1, 2, 3] [1, 2, 3] >>> ['cat', 'bat', 'rat', 'elephant'] ['cat', 'bat', 'rat', 'elephant'] >>> ['hello', 3.1415, True, None, 42] ['hello', 3.1415, True, None, 42] 1. >>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam ['cat', 'bat', 'rat', 'elephant']

spam变量1. 仍然只被赋予一个值：列表值。但列表值本身包含多个值。[]是一个空列表，不包含任何值，类似于空字符串''。

### 4.1.1 用下标取得列表中的单个值假定列表['cat', 'bat', 'rat', 'elephant']保存在名为spam的变量中。Python代码spam[0]将求值为'cat'，spam[1]将求值为'bat'，依此类推。列表后面方括号内的整数被称为"下标"。列表中第一个值的下标是0，第二个值的下标是1，第三个值的下标是2，依此类推。图4-1展示了一个赋给spam的列表值，以及下标表达式的求值结果。

图4-1 一个列表值保存在spam变量中，展示了每个下标指向哪个值例如，在交互式环境中输入以下表达式。开始将列表赋给变量spam。 >>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[0] 'cat' >>> spam[1] 'bat' >>> spam[2] 'rat' >>> spam[3] 'elephant' >>> ['cat', 'bat', 'rat', 'elephant'][3] 'elephant' 1. >>> 'Hello ' + spam[0] 2. 'Hello cat' >>> 'The ' + spam[1] + ' ate the ' + spam[0] + '.' 'The bat ate the cat.'

请注意，表达式'Hello ' + spam[0] 1. 求值为'Hello ' + 'cat'，因为spam[0]求值为字符串'cat'。这个表达式也因此求值为字符串'Hello cat'2. 。

如果使用的下标超出了列表中值的个数，Python将给出IndexError出错信息。>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[10000] Traceback (most recent call last): File "<pyshell#9>", line 1, in <module> spam[10000] IndexError: list index out of range

下标只能是整数，不能是浮点值。下面的例子将导致TypeError错误：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[1] 'bat' >>> spam[1.0] Traceback (most recent call last): File "<pyshell#13>", line 1, in <module> spam[1.0] TypeError: list indices must be integers, not float >>> spam[int(1.0)] 'bat'

列表也可以包含其他列表值。这些列表的列表中的值，可以通过多重下标来访问，像这样：>>> spam = [['cat', 'bat'], [10, 20, 30, 40, 50]] >>> spam[0] ['cat', 'bat'] >>> spam[0][1] 'bat' >>> spam[1][4] 50

第一个下标表明使用哪个列表值，第二个下标表明该列表值中的值。例如，spam[0][1]打印出'bat'，即第一个列表中的第二个值。如果只使用一个下标，程序将打印出该下标处的完整列表值。

### 4.1.2 负数下标虽然下标从0开始并向上增长，但也可以用负整数作为下标。整数值−1指的是列表中的最后一个下标，−2指的是列表中倒数第二个下标，以此类推。在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[-1] 'elephant' >>> spam[-3] 'bat' >>> 'The ' + spam[-1] + ' is afraid of the ' + spam[-3] + '.' 'The elephant is afraid of the bat.'

### 4.1.3 利用切片取得子列表就像下标可以从列表中取得单个值一样，"切片"可以从列表中取得多个值，结果是一个新列表。切片输入在一对方括号中，像下标一样，但它有两个冒号分隔的整数。请注意下标和切片的不同。

- spam[2]是一个列表和下标（一个整数）。

- spam[1:4]是一个列表和切片（两个整数）。

在一个切片中，第一个整数是切片开始处的下标。第二个整数是切片结束处的下标。切片向上增长，直至第二个下标的值，但不包括它。切片求值为一个新的列表值。在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[0:4] ['cat', 'bat', 'rat', 'elephant'] >>> spam[1:3] ['bat', 'rat'] >>> spam[0:-1] ['cat', 'bat', 'rat']

作为快捷方法，你可以省略切片中冒号两边的一个下标或两个下标。省略第一个下标相当于使用0，或列表的开始。省略第二个下标相当于使用列表的长度，意味着切片直至列表的末尾。在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[:2] ['cat', 'bat'] >>> spam[1:] ['bat', 'rat', 'elephant'] >>> spam[:] ['cat', 'bat', 'rat', 'elephant']

### 4.1.4 用len()取得列表的长度

len()函数将返回传递给它的列表中值的个数，就像它能计算字符串中字符的个数一样。在交互式环境中输入以下代码：>>> spam = ['cat', 'dog', 'moose'] >>> len(spam) 3

### 4.1.5 用下标改变列表中的值一般情况下，赋值语句左边是一个变量名，就像spam = 4。但是，也可以使用列表的下标来改变下标处的值。例如，spam[1] = 'aardvark'意味着"将列表spam下标1处的值赋值为字符串'aardvark'。在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam[1] = 'aardvark' >>> spam ['cat', 'aardvark', 'rat', 'elephant'] >>> spam[2] = spam[1] >>> spam ['cat', 'aardvark', 'aardvark', 'elephant'] >>> spam[-1] = 12345 >>> spam ['cat', 'aardvark', 'aardvark', 12345]

### 4.1.6 列表连接和列表复制

+操作符可以连接两个列表，得到一个新列表，就像它将两个字符串合并成一个新字符串一样。*操作符可以用于一个列表和一个整数，实现列表的复制。在交互式环境中输入以下代码：>>> [1, 2, 3] + ['A', 'B', 'C'] [1, 2, 3, 'A', 'B', 'C'] >>> ['X', 'Y', 'Z'] * 3 ['X', 'Y', 'Z', 'X', 'Y', 'Z', 'X', 'Y', 'Z'] >>> spam = [1, 2, 3] >>> spam = spam + ['A', 'B', 'C'] >>> spam [1, 2, 3, 'A', 'B', 'C']

### 4.1.7 用del语句从列表中删除值

del语句将删除列表中下标处的值，表中被删除值后面的所有值，都将向前移动一个下标。例如，在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> del spam[2] >>> spam ['cat', 'bat', 'elephant'] >>> del spam[2] >>> spam ['cat', 'bat']

del语句也可用于一个简单变量，删除它，作用就像是"取消赋值"语句。如果在删除之后试图使用该变量，就会遇到NameError错误，因为该变量已不再存在。

在实践中，你几乎永远不需要删除简单变量。del语句几乎总是用于删除列表中的值。

## 4.2 使用列表当你第一次开始编程时，很容易会创建许多独立的变量，来保存一组类似的值。例如，如果要保存我的猫的名字，可能会写出这样的代码：catName1 = 'Zophie' catName2 = 'Pooka' catName3 = 'Simon' catName4 = 'Lady Macbeth' catName5 = 'Fat-tail' catName6 = 'Miss Cleo'

事实表明这是一种不好的编程方式。举一个例子，如果猫的数目发生改变，程序就不得不增加变量，来保存更多的猫。这种类型的程序也有很多重复或几乎相等的代码。考虑下面的程序中有多少重复代码，在文本编辑器中输入它并保存为allMyCats1.py：print('Enter the name of cat 1:') catName1 = input() print('Enter the name of cat 2:') catName2 = input() print('Enter the name of cat 3:') catName3 = input() print('Enter the name of cat 4:') catName4 = input() print('Enter the name of cat 5:') catName5 = input() print('Enter the name of cat 6:') catName6 = input() print('The cat names are:') print(catName1 + ' ' + catName2 + ' ' + catName3 + ' ' + catName4 + ' ' + catName5 + ' ' + catName6)

不必使用多个重复的变量，你可以使用单个变量，包含一个列表值。例如，下面是新的改进版本的allMyCats1.py程序。这个新版本使用了一个列表，可以保存用户输入的任意多的猫。在新的文件编辑器窗口中，输入以下代码并保存为allMyCats2.py。catNames = [] while True: print('Enter the name of cat ' + str(len(catNames) + 1) + ' (Or enter nothing to stop.):') name = input() if name == '': break catNames = catNames + [name] # list concatenation print('The cat names are:') for name in catNames: print(' ' + name)

运行这个程序，输出看起来像这样：Enter the name of cat 1 (Or enter nothing to stop.): Zophie Enter the name of cat 2 (Or enter nothing to stop.): Pooka Enter the name of cat 3 (Or enter nothing to stop.): Simon Enter the name of cat 4 (Or enter nothing to stop.): Lady Macbeth Enter the name of cat 5 (Or enter nothing to stop.): Fat-tail Enter the name of cat 6 (Or enter nothing to stop.): Miss Cleo Enter the name of cat 7 (Or enter nothing to stop.): The cat names are: Zophie Pooka Simon Lady Macbeth Fat-tail Miss Cleo

使用列表的好处在于，现在数据放在一个结构中，所以程序能够更灵活的处理数据，比放在一些重复的变量中方便。

### 4.2.1 列表用于循环在第2章中，你学习了使用循环，对一段代码执行一定次数。从技术上说，循环是针对一个列表或类似列表中的每个值，重复地执行代码块。例如，如果执行以下代码：for i in range(4): print(i)

程序的输出将是：0 1 2 3

这是因为range(4)的返回值是类似列表的值。Python认为它类似于[0, 1, 2, 3]。下面的程序和前面的程序输出相同：for i in [0, 1, 2, 3]: print(i)

前面的for循环实际上是在循环执行它的子句，在每次迭代中，让变量依次设置为列表中的值。

注意在本书中，我使用术语"类似列表"，来指技术上称为"序列"的数据类型。但是，你不需要知道这个术语的技术定义。

一个常见的Python技巧，是在for循环中使用range(len(someList))，迭代列表的每一个下标。例如，在交互式环境中输入以下代码：>>> supplies = ['pens', 'staplers', 'flame-throwers', 'binders'] >>> for i in range(len(supplies)):print('Index ' + str(i) + ' in supplies is: ' + supplies[i]) Index 0 in supplies is: pens Index 1 in supplies is: staplers Index 2 in supplies is: flame-throwers Index 3 in supplies is: binders

在前面的循环中使用range(len(supplies))很方便，这是因为，循环中的代码可以访问下标（通过变量i），以及下标处的值（通过supplies[i]）。最妙的是，range(len(supplies))将迭代supplies的所有下标，无论它包含多少表项。

### 4.2.2 in和not in操作符利用in和not in操作符，可以确定一个值是否在列表中。像其他操作符一样，in和not in用在表达式中，连接两个值：一个要在列表中查找的值，以及待查找的列表。这些表达式将求值为布尔值。在交互式环境中输入以下代码：>>> 'howdy' in ['hello', 'hi', 'howdy', 'heyas'] True >>> spam = ['hello', 'hi', 'howdy', 'heyas'] >>> 'cat' in spam False >>> 'howdy' not in spam False >>> 'cat' not in spam True

例如，下面的程序让用户输入一个宠物名字，然后检查该名字是否在宠物列表中。打开一个新的文件编辑器窗口，输入以下代码，并保存为myPets.py：myPets = ['Zophie', 'Pooka', 'Fat-tail'] print('Enter a pet name:') name = input() if name not in myPets: print('I do not have a pet named ' + name) else: print(name + ' is my pet.')

输出可能像这样：Enter a pet name: Footfoot I do not have a pet named Footfoot

### 4.2.3 多重赋值技巧多重赋值技巧是一种快捷方式，让你在一行代码中，用列表中的值为多个变量赋值。所以不必像这样：>>> cat = ['fat', 'black', 'loud'] >>> size = cat[0] >>> color = cat[1] >>> disposition = cat[2]

而是输入下面的代码：>>> cat = ['fat', 'black', 'loud'] >>> size, color, disposition = cat

变量的数目和列表的长度必须严格相等，否则Python将给出ValueError：>>> cat = ['fat', 'black', 'loud'] >>> size, color, disposition, name = cat Traceback (most recent call last): File "<pyshell#84>", line 1, in <module> size, color, disposition, name = cat ValueError: need more than 3 values to unpack

## 4.3 增强的赋值操作在对变量赋值时，常常会用到变量本身。例如，将42赋给变量spam之后，用下面的代码让spam的值增加1：>>> spam = 42 >>> spam = spam + 1 >>> spam 43

作为一种快捷方式，可以用增强的赋值操作符+=来完成同样的事：>>> spam = 42 >>> spam += 1 >>> spam 43

针对+、-、*、/和%操作符，都有增强的赋值操作符，如表4-1所示。

表4-1 增强的赋值操作符增强的赋值语句等价的赋值语句

spam += 1

spam = spam + 1

spam -= 1

spam = spam - 1

spam *= 1

spam = spam * 1

spam /= 1

spam = spam / 1

spam %= 1

spam = spam % 1

+=操作符也可以完成字符串和列表的连接，*=操作符可以完成字符串和列表的复制。在交互式环境中输入以下代码：>>> spam = 'Hello' >>> spam += ' world!' >>> spam 'Hello world!' >>> bacon = ['Zophie'] >>> bacon *= 3 >>> bacon ['Zophie', 'Zophie', 'Zophie']

## 4.4 方法方法和函数是一回事，只是它是调用在一个值上。例如，如果一个列表值存储在spam中，你可以在这个列表上调用index()列表方法（稍后我会解释），就像spam.index('hello')一样。方法部分跟在这个值后面，以一个句点分隔。

每种数据类型都有它自己的一组方法。例如，列表数据类型有一些有用的方法，用来查找、添加、删除或操作列表中的值。

### 4.4.1 用index()方法在列表中查找值列表值有一个index()方法，可以传入一个值，如果该值存在于列表中，就返回它的下标。如果该值不在列表中，Python就报ValueError。在交互式环境中输入以下代码：>>> spam = ['hello', 'hi', 'howdy', 'heyas'] >>> spam.index('hello') 0 >>> spam.index('heyas') 3 >>> spam.index('howdy howdy howdy') Traceback (most recent call last): File "<pyshell#31>", line 1, in <module> spam.index('howdy howdy howdy') ValueError: 'howdy howdy howdy' is not in list

如果列表中存在重复的值，就返回它第一次出现的下标。在交互式环境中输入以下代码，注意index()返回1，而不是3：>>> spam = ['Zophie', 'Pooka', 'Fat-tail', 'Pooka'] >>> spam.index('Pooka') 1

### 4.4.2 用append()和insert()方法在列表中添加值要在列表中添加新值，就使用append()和 insert()方法。在交互式环境中输入以下代码，对变量spam中的列表调用append()方法：>>> spam = ['cat', 'dog', 'bat'] >>> spam.append('moose') >>> spam ['cat', 'dog', 'bat', 'moose']

前面的append()方法调用，将参数添加到列表末尾。insert()方法可以在列表任意下标处插入一个值。insert()方法的第一个参数是新值的下标，第二个参数是要插入的新值。在交互式环境中输入以下代码：>>> spam = ['cat', 'dog', 'bat'] >>> spam.insert(1, 'chicken') >>> spam ['cat', 'chicken', 'dog', 'bat']

请注意，代码是spam.append('moose')和spam.insert(1, 'chicken')，而不是spam = spam.append('moose')和spam = spam.insert(1, 'chicken')。append()和insert()都不会将spam的新值作为其返回值（实际上，append()和insert()的返回值是None，所以你肯定不希望将它保存为变量的新值）。但是，列表被"当场"修改了。在4.6.1节"可变和不变数据类型"中，将更详细地介绍当场修改一个列表。

方法属于单个数据类型。append()和insert()方法是列表方法，只能在列表上调用，不能在其他值上调用，例如字符串和整型。在交互式环境中输入以下代码，注意产生的AttributeError错误信息：>>> eggs = 'hello' >>> eggs.append('world') Traceback (most recent call last): File "<pyshell#19>", line 1, in <module> eggs.append('world') AttributeError: 'str' object has no attribute 'append' >>> bacon = 42 >>> bacon.insert(1, 'world') Traceback (most recent call last): File "<pyshell#22>", line 1, in <module> bacon.insert(1, 'world') AttributeError: 'int' object has no attribute 'insert'

### 4.4.3 用remove()方法从列表中删除值给 remove()方法传入一个值，它将从被调用的列表中删除。在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam.remove('bat') >>> spam ['cat', 'rat', 'elephant']

试图删除列表中不存在的值，将导致ValueError错误。例如，在交互式环境中输入以下代码，注意显示的错误：>>> spam = ['cat', 'bat', 'rat', 'elephant'] >>> spam.remove('chicken') Traceback (most recent call last): File "<pyshell#11>", line 1, in <module> spam.remove('chicken') ValueError: list.remove(x): x not in list

如果该值在列表中出现多次，只有第一次出现的值会被删除。在交互式环境中输入以下代码：>>> spam = ['cat', 'bat', 'rat', 'cat', 'hat', 'cat'] >>> spam.remove('cat') >>> spam ['bat', 'rat', 'cat', 'hat', 'cat']

如果知道想要删除的值在列表中的下标，del语句就很好用。如果知道想要从列表中删除的值，remove()方法就很好用。

### 4.4.4 用sort()方法将列表中的值排序数值的列表或字符串的列表，能用sort()方法排序。例如，在交互式环境中输入以下代码：>>> spam = [2, 5, 3.14, 1, -7] >>> spam.sort() >>> spam [-7, 1, 2, 3.14, 5] >>> spam = ['ants', 'cats', 'dogs', 'badgers', 'elephants'] >>> spam.sort() >>> spam ['ants', 'badgers', 'cats', 'dogs', 'elephants']

也可以指定reverse关键字参数为True，让sort()按逆序排序。在交互式环境中输入以下代码：>>> spam.sort(reverse=True) >>> spam ['elephants', 'dogs', 'cats', 'badgers', 'ants']

关于sort()方法，你应该注意3件事。首先，sort()方法当场对列表排序。不要写出spam = spam.sort()这样的代码，试图记录返回值。

其次，不能对既有数字又有字符串值的列表排序，因为Python不知道如何比较它们。在交互式环境中输入以下代码，注意TypeError错误：>>> spam = [1, 3, 2, 4, 'Alice', 'Bob'] >>> spam.sort() Traceback (most recent call last): File "<pyshell#70>", line 1, in <module> spam.sort() TypeError: unorderable types: str() < int()

第三，sort()方法对字符串排序时，使用"ASCII字符顺序"，而不是实际的字典顺序。这意味着大写字母排在小写字母之前。因此在排序时，小写的a在大写的Z之后。例如，在交互式环境中输入以下代码：>>> spam = ['Alice', 'ants', 'Bob', 'badgers', 'Carol', 'cats'] >>> spam.sort() >>> spam ['Alice', 'Bob', 'Carol', 'ants', 'badgers', 'cats']

如果需要按照普通的字典顺序来排序，就在sort()方法调用时，将关键字参数key设置为str.lower。>>> spam = ['a', 'z', 'A', 'Z'] >>> spam.sort(key=str.lower) >>> spam ['a', 'A', 'z', 'Z']

这将导致sort()方法将列表中所有的表项当成小写，但实际上并不会改变它们在列表中的值。

## 4.5 例子程序：神奇8球和列表前一章我们写过神奇8球程序。利用列表，可以写出更优雅的版本。不是用一些几乎一样的elif语句，而是创建一个列表，针对它编码。打开一个新的文件编辑器窗口，输入以下代码，并保存为magic8Ball2.py：import random messages = ['It is certain', 'It is decidedly so', 'Yes definitely', 'Reply hazy try again', 'Ask again later', 'Concentrate and ask again', 'My reply is no', 'Outlook not so good', 'Very doubtful'] print(messages[random.randint(0, len(messages) - 1)])

Python中缩进规则的例外在大多数情况下，代码行的缩进告诉Python它属于哪一个代码块。但是，这个规则有几个例外。例如在源代码文件中，列表实际上可以跨越几行。这些行的缩进并不重要。Python知道，没有看到结束方括号，列表就没有结束。例如，代码可以看起来像这样：spam = ['apples', 'oranges', 'bananas', 'cats'] print(spam)

当然，从实践的角度来说，大部分人会利用Python的行为，让他们的列表看起来漂亮且可读，就像神奇8球程序中的消息列表一样。

也可以在行末使用续行字符\，将一条指令写成多行。可以把\看成是"这条指令在下一行继续"。\续行字符之后的一行中，缩进并不重要。例如，下面是有效的Python代码：print('Four score and seven ' + \ 'years ago...')

如果希望将一长行的Python代码安排得更为可读，这些技巧是有用的。

运行这个程序，你会看到它与前面的magic8Ball.py程序效果一样。

请注意用作messages下标的表达式：random.randint(0, len(messages) - 1)。这产生了一个随机数作为下标，不论messages的大小是多少。也就是说，你会得到0与len(messages) - 1之间的一个随机数。这种方法的好处在于，很容易向列表添加或删除字符串，而不必改变其他行的代码。如果稍后更新代码，就可以少改几行代码，引入缺陷的可能性也更小。

## 4.6 类似列表的类型：字符串和元组列表并不是唯一表示序列值的数据类型。例如，字符串和列表实际上很相似，只要你认为字符串是单个文本字符的列表。对列表的许多操作，也可以作用于字符串：按下标取值、切片、用于for循环、用于len()，以及用于in和not in操作符。为了看到这种效果，在交互式环境中输入以下代码：>>> name = 'Zophie' >>> name[0] 'Z' >>> name[-2] 'i' >>> name[0:4] 'Zoph' >>> 'Zo' in name True >>> 'z' in name False >>> 'p' not in name False >>> for i in name:print('* * * ' + i + ' * * *') * * * Z * * * * * * o * * * * * * p * * * * * * h * * * * * * i * * * * * * e * * *

### 4.6.1 可变和不可变数据类型但列表和字符串在一个重要的方面是不同的。列表是"可变的"数据类型，它的值可以添加、删除或改变。但是，字符串是"不可变的"，它不能被更改。尝试对字符串中的一个字符重新赋值，将导致TypeError错误。在交互式环境中输入以下代码，你就会看到：>>> name = 'Zophie a cat' >>> name[7] = 'the' Traceback (most recent call last): File "<pyshell#50>", line 1, in <module> name[7] = 'the' TypeError: 'str' object does not support item assignment

"改变"一个字符串的正确方式，是使用切片和连接。构造一个"新的"字符串，从老的字符串那里复制一些部分。在交互式环境中输入以下代码：>>> name = 'Zophie a cat' >>> newName = name[0:7] + 'the' + name[8:12] >>> name 'Zophie a cat' >>> newName 'Zophie the cat'

我们用[0:7]和[8:12]来指那些不想替换的字符。请注意，原来的'Zophie a cat'字符串没有被修改，因为字符串是不可变的。尽管列表值是可变的，但下面代码中的第二行并没有修改列表eggs：>>> eggs = [1, 2, 3] >>> eggs = [4, 5, 6] >>> eggs [4, 5, 6]

这里eggs中的列表值并没有改变，而是整个新的不同的列表值([4, 5, 6])，覆写了老的列表值。如图4-2所示。

图4-2 当eggs = [4, 5, 6]被执行时，eggs的内容被新的列表值取代如果你确实希望修改eggs中原来的列表，让它包含[4, 5, 6]，就要这样做：>>> eggs = [1, 2, 3] >>> del eggs[2] >>> del eggs[1] >>> del eggs[0] >>> eggs.append(4) >>> eggs.append(5) >>> eggs.append(6) >>> eggs [4, 5, 6]

在第一个例子中，eggs最后的列表值与它开始的列表值是一样的。只是这个列表被改变了，而不是被覆写。图4-3展示了前面交互式脚本的例子中，前7行代码所做的7次改动。

图4-3 del语句和append()方法当场修改了同一个列表值改变一个可变数据类型的值（就像前面例子中del语句和append()方法所做的事），当场改变了该值，因为该变量的值没有被一个新的列表值取代。

区分可变与不可变类型，似乎没有什么意义，但4.7.1节"传递引用"将解释，使用可变参数和不可变参数调用函数时产生的不同行为。首先，让我们来看看元组数据类型，它是列表数据类型的不可变形式。

### 4.6.2 元组数据类型除了两个方面，"元组"数据类型几乎与列表数据类型一样。首先，元组输入时用圆括号()，而不是用方括号[]。例如，在交互式环境中输入以下代码：>>> eggs = ('hello', 42, 0.5) >>> eggs[0] 'hello' >>> eggs[1:3] (42, 0.5) >>> len(eggs) 3

但元组与列表的主要区别还在于，元组像字符串一样，是不可变的。元组不能让它们的值被修改、添加或删除。在交互式环境中输入以下代码，注意TypeError出错信息：>>> eggs = ('hello', 42, 0.5) >>> eggs[1] = 99 Traceback (most recent call last): File "<pyshell#5>", line 1, in <module> eggs[1] = 99 TypeError: 'tuple' object does not support item assignment

如果元组中只有一个值，你可以在括号内该值的后面跟上一个逗号，表明这种情况。否则，Python将认为，你只是在一个普通括号内输入了一个值。逗号告诉Python，这是一个元组（不像其他编程语言，Python接受列表或元组中最后表项后面跟的逗号）。在交互式环境中，输入以下的type()函数调用，看看它们的区别：>>> type(('hello',)) <class 'tuple'> >>> type(('hello')) <class 'str'>

你可以用元组告诉所有读代码的人，你不打算改变这个序列的值。如果需要一个永远不会改变的值的序列，就使用元组。使用元组而不是列表的第二个好处在于，因为它们是不可变的，它们的内容不会变化，Python可以实现一些优化，让使用元组的代码比使用列表的代码更快。

### 4.6.3 用list()和tuple()函数来转换类型正如str(42)将返回'42'，即整数42的字符串表示形式，函数list()和tuple()将返回传递给它们的值的列表和元组版本。在交互式环境中输入以下代码，注意返回值与传入值是不同的数据类型：>>> tuple(['cat', 'dog', 5]) ('cat', 'dog', 5) >>> list(('cat', 'dog', 5)) ['cat', 'dog', 5] >>> list('hello') ['h', 'e', 'l', 'l', 'o']

如果需要元组值的一个可变版本，将元组转换成列表就很方便。

## 4.7 引用正如你看到的，变量保存字符串和整数值。在交互式环境中输入以下代码：>>> spam = 42 >>> cheese = spam >>> spam = 100 >>> spam 100 >>> cheese 42

你将42赋给spam变量，然后拷贝spam中的值，将它赋给变量cheese。当稍后将spam中的值改变为100时，这不会影响cheese中的值。这是因为spam和cheese是不同的变量，保存了不同的值。

但列表不是这样的。当你将列表赋给一个变量时，实际上是将列表的"引用"赋给了该变量。引用是一个值，指向某些数据。列表引用是指向一个列表的值。这里有一些代码，让这个概念更容易理解。在交互式环境中输入以下代码：1. >>> spam = [0, 1, 2, 3, 4, 5] 2. >>> cheese = spam 3. >>> cheese[1] = 'Hello!' >>> spam [0, 'Hello!', 2, 3, 4, 5] >>> cheese [0, 'Hello!', 2, 3, 4, 5]

这可能让你感到奇怪。代码只改变了cheese列表，但似乎cheese和spam列表同时发生了改变。

当创建列表时1. ，你将对它的引用赋给了变量。但下一行2. 只是将spam中的列表引用拷贝到cheese，而不是列表值本身。这意味着存储在spam和cheese中的值，现在指向了同一个列表。底下只有一个列表，因为列表本身实际从未复制。所以当你修改cheese变量的第一个元素时3. ，也修改了spam指向的同一个列表。

记住，变量就像包含着值的盒子。本章前面的图显示列表在盒子中，这并不准确，因为列表变量实际上没有包含列表，而是包含了对列表的"引用"（这些引用包含一些ID数字，Python在内部使用这些ID，但是你可以忽略）。利用盒子作为变量的隐喻，图4-4展示了列表被赋给spam变量时发生的情形。

图4-4 spam = [0, 1, 2, 3, 4, 5]保存了对列表的引用，而非实际列表然后，在图4-5中，spam中的引用被复制给cheese。只有新的引用被创建并保存在cheese中，而非新的列表。请注意，两个引用都指向同一个列表。

图4-5 spam = cheese复制了引用，而非列表当你改变cheese指向的列表时，spam指向的列表也发生了改变，因为cheese和spam都指向同一个列表，如图4-6所示。

图4-6 cheese[1] = 'Hello!'修改了两个变量指向的列表变量包含对列表值的引用，而不是列表值本身。但对于字符串和整数值，变量就包含了字符串或整数值。在变量必须保存可变数据类型的值时，例如列表或字典，Python就使用引用。对于不可变的数据类型的值，例如字符串、整型或元组，Python变量就保存值本身。

虽然Python变量在技术上包含了对列表或字典值的引用，但人们通常随意地说，该变量包含了列表或字典。

### 4.7.1 传递引用要理解参数如何传递给函数，引用就特别重要。当函数被调用时，参数的值被复制给变元。对于列表（以及字典，我将在下一章中讨论），这意味着变元得到的是引用的拷贝。要看看这导致的后果，请打开一个新的文件编辑器窗口，输入以下代码，并保存为passingReference.py：def eggs(someParameter): someParameter.append('Hello') spam = [1, 2, 3] eggs(spam) print(spam)

请注意，当eggs()被调用时，没有使用返回值来为spam赋新值。相反，它直接当场修改了该列表。在运行时，该程序产生输出如下：[1, 2, 3, 'Hello']

尽管spam和someParameter包含了不同的引用，但它们都指向相同的列表。这就是为什么函数内的append('Hello')方法调用在函数调用返回后，仍然会对该列表产生影响。

请记住这种行为：如果忘了Python处理列表和字典变量时采用这种方式，可能会导致令人困惑的缺陷。

### 4.7.2 copy模块的copy()和deepcopy()函数在处理列表和字典时，尽管传递引用常常是最方便的方法，但如果函数修改了传入的列表或字典，你可能不希望这些变动影响原来的列表或字典。要做到这一点，Python提供了名为copy的模块，其中包含copy()和deepcopy()函数。第一个函数copy.copy()，可以用来复制列表或字典这样的可变值，而不只是复制引用。在交互式环境中输入以下代码：>>> import copy >>> spam = ['A', 'B', 'C', 'D'] >>> cheese = copy.copy(spam) >>> cheese[1] = 42 >>> spam ['A', 'B', 'C', 'D'] >>> cheese ['A', 42, 'C', 'D']

现在spam和cheese变量指向独立的列表，这就是为什么当你将42赋给下标7时，只有cheese中的列表被改变。在图4-7中可以看到，两个变量的引用ID数字不再一样，因为它们指向了独立的列表。

图4-7 cheese = copy.copy(spam)创建了第二个列表，能独立于第一个列表修改如果要复制的列表中包含了列表，那就使用copy.deepcopy()函数来代替。deepcopy()函数将同时复制它们内部的列表。

## 4.8 小结列表是有用的数据类型，因为它们让你写代码处理一组可以修改的值，同时仅用一个变量。在本书后面的章节中，你会看到一些程序利用列表来完成工作。没有列表，这些工作很困难，甚至不可能完成。

列表是可变的，这意味着它们的内容可以改变。元组和字符串虽然在某些方面像列表，却是不可变的，不能被修改。包含一个元组或字符串的变量，可以被一个新的元组或字符串覆写，但这和现场修改原来的值不是一回事，不像append()和remove()方法在列表上的效果。

变量不直接保存列表值，它们保存对列表的"引用"。在复制变量或将列表作为函数调用的参数时，这一点很重要。因为被复制的只是列表引用，所以要注意，对该列表的所有改动都可能影响到程序中的其他变量。如果需要对一个变量中的列表修改，同时不修改原来的列表，就可以用copy()或deepcopy()。

## 4.9 习题

1．什么是[]？

2．如何将'hello'赋给列表的第三个值，而列表保存在名为spam的变量中？（假定变量包含[2, 4, 6, 8, 10]）。

对接下来的3个问题，假定spam包含列表['a', 'b', 'c', 'd']。

3．spam[int('3' * 2) / 11]求值为多少？

4．spam[-1]求值为多少？

5．spam[:2]求值为多少？

对接下来的3个问题。假定bacon包含列表[3.14, 'cat', 11, 'cat', True]。

6．bacon.index('cat')求值为多少？

7．bacon.append(99)让bacon中的列表值变成什么样？

8．bacon.remove('cat')让bacon中的列表时变成什么样？

9．列表连接和复制的操作符是什么？

10．append()和insert()列表方法之间的区别是什么？

11．从列表中删除值有哪两种方法？

12．请说出列表值和字符串的几点相似之处。

13．列表和元组之间的区别是什么？

14．如果元组中只有一个整数值42，如何输入该元组？

15．如何从列表值得到元组形式？如何从元组值得到列表形式？

16．"包含"列表的变量，实际上并未真地直接包含列表。它们包含的是什么？

17．copy.copy()和copy.deepcopy()之间的区别是什么？

## 4.10 实践项目作为实践，编程完成下列任务。

### 4.10.1 逗号代码假定有下面这样的列表：spam = ['apples', 'bananas', 'tofu', 'cats']

编写一个函数，它以一个列表值作为参数，返回一个字符串。该字符串包含所有表项，表项之间以逗号和空格分隔，并在最后一个表项之前插入and。例如，将前面的spam列表传递给函数，将返回'apples, bananas, tofu, and cats'。但你的函数应该能够处理传递给它的任何列表。

### 4.10.2 字符图网格假定有一个列表的列表，内层列表的每个值都是包含一个字符的字符串，像这样：grid = [['.', '.', '.', '.', '.', '.'], ['.', 'O', 'O', '.', '.', '.'], ['O', 'O', 'O', 'O', '.', '.'], ['O', 'O', 'O', 'O', 'O', '.'], ['.', 'O', 'O', 'O', 'O', 'O'], ['O', 'O', 'O', 'O', 'O', '.'], ['O', 'O', 'O', 'O', '.', '.'], ['.', 'O', 'O', '.', '.', '.'], ['.', '.', '.', '.', '.', '.']]

你可以认为grid[x][y]是一幅"图"在x、y坐标处的字符，该图由文本字符组成。原点(0, 0)在左上角，向右x坐标增加，向下y坐标增加。

复制前面的网格值，编写代码用它打印出图像。..OO.OO.. .OOOOOOO. .OOOOOOO. ..OOOOO.. ...OOO... ....O....

提示你需要使用循环嵌套循环，打印出grid[0][0]，然后grid[1][0]，然后grid[2][0]，以此类推，直到grid[8][0]。这就完成第一行，所以接下来打印换行。然后程序将打印出grid[0][1]，然后grid[1][1]，然后grid[2][1]，以此类推。程序最后将打印出grid[8][5]。

而且，如果你不希望在每次print()调用后都自动打印换行，记得向print()传递end关键字参数。

# 第5章字典和结构化数据在本章中，我将介绍字典数据类型，它提供了一种灵活的访问和组织数据的方式。然后，结合字典与前一章中关于列表的知识，你将学习如何创建一个数据结构，对井字棋盘建模。

## 5.1 字典数据类型像列表一样，"字典"是许多值的集合。但不像列表的下标，字典的索引可以使用许多不同数据类型，不只是整数。字典的索引被称为"键"，键及其关联的值称为"键-值"对。

在代码中，字典输入时带花括号{}。在交互式环境中输入以下代码：>>> myCat = {'size': 'fat', 'color': 'gray', 'disposition': 'loud'}

这将一个字典赋给myCat变量。这个字典的键是'size'、'color'和'disposition'。这些键相应的值是'fat'、'gray'和'loud'。可以通过它们的键访问这些值：>>> myCat['size'] 'fat' >>> 'My cat has ' + myCat['color'] + ' fur.' 'My cat has gray fur.'

字典仍然可以用整数值作为键，就像列表使用整数值作为下标一样，但它们不必从0开始，可以是任何数字。>>> spam = {12345: 'Luggage Combination', 42: 'The Answer'}

### 5.1.1 字典与列表不像列表，字典中的表项是不排序的。名为spam的列表中，第一个表项是spam[0]。但字典中没有"第一个"表项。虽然确定两个列表是否相同时，表项的顺序很重要，但在字典中，键-值对输入的顺序并不重要。在交互式环境中输入以下代码：>>> spam = ['cats', 'dogs', 'moose'] >>> bacon = ['dogs', 'moose', 'cats'] >>> spam == bacon False >>> eggs = {'name': 'Zophie', 'species': 'cat', 'age': '8'} >>> ham = {'species': 'cat', 'age': '8', 'name': 'Zophie'} >>> eggs == ham True

因为字典是不排序的，所以不能像列表那样切片。

尝试访问字典中不存在的键，将导致KeyError出错信息。这很像列表的"越界"IndexError出错信息。在交互式环境中输入以下代码，并注意显示的出错信息，因为没有'color'键：>>> spam = {'name': 'Zophie', 'age': 7} >>> spam['color'] Traceback (most recent call last): File "", line 1, in spam['color'] KeyError: 'color'

尽管字典是不排序的，但可以用任意值作为键，这一点让你能够用强大的方式来组织数据。假定你希望程序保存朋友生日的数据，就可以使用一个字典，用名字作为键，用生日作为值。打开一个新的文件编辑窗口，输入以下代码，并保存为birthdays.py：1. birthdays = {'Alice': 'Apr 1', 'Bob': 'Dec 12', 'Carol': 'Mar 4'} while True: print('Enter a name: (blank to quit)') name = input() if name == '': break 2. if name in birthdays: 3. print(birthdays[name] + ' is the birthday of ' + name) else: print('I do not have birthday information for ' + name) print('What is their birthday?') bday = input() 4. birthdays[name] = bday print('Birthday database updated.')

你创建了一个初始的字典，将它保存在birthdays中1. 。用in关键字，可以看看输入的名字是否作为键存在于字典中2. ，就像查看列表一样。如果该名字在字典中，你可以用方括号访问关联的值3. 。如果不在，你可以用同样的方括号语法和赋值操作符添加它4. 。

运行这个程序，结果看起来如下所示：Enter a name: (blank to quit) Alice Apr 1 is the birthday of Alice Enter a name: (blank to quit) Eve I do not have birthday information for Eve What is their birthday? Dec 5 Birthday database updated. Enter a name: (blank to quit) Eve Dec 5 is the birthday of Eve Enter a name: (blank to quit)

当然，在程序终止时，你在这个程序中输入的所有数据都丢失了。在第 8章中，你将学习如何将数据保存在硬盘的文件中。

### 5.1.2 keys()、values()和items()方法有3个字典方法，它们将返回类似列表的值，分别对应于字典的键、值和键-值对：keys()、values()和items()。这些方法返回的值不是真正的列表，它们不能被修改，没有append()方法。但这些数据类型（分别是dict_keys、dict_values和dict_items）可以用于for循环。为了看看这些方法的工作原理，请在交互式环境中输入以下代码：>>> spam = {'color': 'red', 'age': 42} >>> for v in spam.values():print(v) red 42

这里，for循环迭代了spam字典中的每个值。for循环也可以迭代每个键，或者键-值对：>>> for k in spam.keys():print(k) color age >>> for i in spam.items():print(i) ('color', 'red') ('age', 42)

利用keys()、values()和items()方法，循环分别可以迭代键、值或键-值对。请注意，items()方法返回的dict_items值中，包含的是键和值的元组。

如果希望通过这些方法得到一个真正的列表，就把类似列表的返回值传递给 list函数。在交互式环境中输入以下代码：>>> spam = {'color': 'red', 'age': 42} >>> spam.keys() dict_keys(['color', 'age']) >>> list(spam.keys()) ['color', 'age']

list(spam.keys())代码行接受keys()函数返回的dict_keys值，并传递给list()。然后返回一个列表，即['color', 'age']。

也可以利用多重赋值的技巧，在for循环中将键和值赋给不同的变量。在交互式环境中输入以下代码：>>> spam = {'color': 'red', 'age': 42} >>> for k, v in spam.items():print('Key: ' + k + ' Value: ' + str(v)) Key: age Value: 42 Key: color Value: red

### 5.1.3 检查字典中是否存在键或值回忆一下，前一章提到，in和not in操作符可以检查值是否存在于列表中。也可以利用这些操作符，检查某个键或值是否存在于字典中。在交互式环境中输入以下代码：>>> spam = {'name': 'Zophie', 'age': 7} >>> 'name' in spam.keys() True >>> 'Zophie' in spam.values() True >>> 'color' in spam.keys() False >>> 'color' not in spam.keys() True >>> 'color' in spam False

请注意，在前面的例子中，'color' in spam本质上是一个简写版本。相当于'color' in spam.keys()。这种情况总是对的：如果想要检查一个值是否为字典中的键，就可以用关键字in（或not in），作用于该字典本身。

### 5.1.4 get()方法在访问一个键的值之前，检查该键是否存在于字典中，这很麻烦。好在，字典有一个get()方法，它有两个参数：要取得其值的键，以及如果该键不存在时，返回的备用值。

在交互式环境中输入以下代码：>>> picnicItems = {'apples': 5, 'cups': 2} >>> 'I am bringing ' + str(picnicItems.get('cups', 0)) + ' cups.' 'I am bringing 2 cups.' >>> 'I am bringing ' + str(picnicItems.get('eggs', 0)) + ' eggs.' 'I am bringing 0 eggs.'

因为picnicItems字典中没有'egg'键，get()方法返回的默认值是0。不使用get()，代码就会产生一个错误消息，就像下面的例子：>>> picnicItems = {'apples': 5, 'cups': 2} >>> 'I am bringing ' + str(picnicItems['eggs']) + ' eggs.' Traceback (most recent call last): File "<pyshell#34>", line 1, in 'I am bringing ' + str(picnicItems['eggs']) + ' eggs.' KeyError: 'eggs'

### 5.1.5 setdefault()方法你常常需要为字典中某个键设置一个默认值，当该键没有任何值时使用它。代码看起来像这样：spam = {'name': 'Pooka', 'age': 5} if 'color' not in spam: spam['color'] = 'black'

setdefault()方法提供了一种方式，在一行中完成这件事。传递给该方法的第一个参数，是要检查的键。第二个参数，是如果该键不存在时要设置的值。如果该键确实存在，方法就会返回键的值。在交互式环境中输入以下代码：>>> spam = {'name': 'Pooka', 'age': 5} >>> spam.setdefault('color', 'black') 'black' >>> spam {'color': 'black', 'age': 5, 'name': 'Pooka'} >>> spam.setdefault('color', 'white') 'black' >>> spam {'color': 'black', 'age': 5, 'name': 'Pooka'}

第一次调用setdefault()时，spam变量中的字典变为{'color': 'black', 'age': 5, 'name': 'Pooka'}。该方法返回值'black'，因为现在该值被赋给键'color'。当spam.setdefault('color', 'white')接下来被调用时，该键的值"没有"被改变成'white'，因为spam变量已经有名为'color'的键。

setdefault()方法是一个很好的快捷方式，可以确保一个键存在。下面有一个小程序，计算一个字符串中每个字符出现的次数。打开一个文件编辑器窗口，输入以下代码，保存为characterCount.py：message = 'It was a bright cold day in April, and the clocks were striking thirteen.' count = {} for character in message: count.setdefault(character, 0) count[character] = count[character] + 1 print(count)

程序循环迭代message字符串中的每个字符，计算每个字符出现的次数。setdefault()方法调用确保了键存在于count字典中（默认值是0），这样在执行count[character] = count[character] + 1时，就不会抛出KeyError错误。程序运行时，输出如下：{' ': 13, ',': 1, '.': 1, 'A': 1, 'I': 1, 'a': 4, 'c': 3, 'b': 1, 'e': 5, 'd': 3, 'g': 2, 'i': 6, 'h': 3, 'k': 2, 'l': 3, 'o': 2, 'n': 4, 'p': 1, 's': 3, 'r': 5, 't': 6, 'w': 2, 'y': 1}

从输出可以看到，小写字母c出现了3次，空格字符出现了13次，大写字母A出现了1次。无论message变量中包含什么样的字符串，这个程序都能工作，即使该字符串有上百万的字符！

## 5.2 漂亮打印如果程序中导入pprint模块，就可以使用pprint()和pformat()函数，它们将"漂亮打印"一个字典的字。如果想要字典中表项的显示比print()的输出结果更干净，这就有用了。修改前面的characterCount.py程序，将它保存为prettyCharacterCount.py。import pprint message = 'It was a bright cold day in April, and the clocks were striking thirteen.' count = {} for character in message: count.setdefault(character, 0) count[character] = count[character] + 1 pprint .pprint( count)

这一次，当程序运行时，输出看起来更干净，键排过序。{' ': 13, ',': 1, '.': 1, 'A': 1, 'I': 1, 'a': 4, 'b': 1, 'c': 3, 'd': 3, 'e': 5, 'g': 2, 'h': 3, 'i': 6, 'k': 2, 'l': 3, 'n': 4, 'o': 2, 'p': 1, 'r': 5, 's': 3, 't': 6, 'w': 2, 'y': 1}

如果字典本身包含嵌套的列表或字典，pprint.pprint()函数就特别有用。

如果希望得到漂亮打印的文本作为字符串，而不是显示在屏幕上，那就调用pprint.pformat()。下面两行代码是等价的：pprint.pprint(someDictionaryValue) print(pprint.pformat(someDictionaryValue))

## 5.3 使用数据结构对真实世界建模甚至在因特网之前，人们也有办法与世界另一边的某人下一盘国际象棋。每个棋手在自己家里放好一个棋盘，然后轮流向对方寄出明信片，描述每一着棋。要做到这一点，棋手需要一种方法，无二义地描述棋盘的状态，以及他们的着法。

在"代数记谱法"中，棋盘空间由一个数字和字母坐标确定，如图5-1所示。

图5-1 代数记谱法中棋盘的坐标棋子用字母表示：K表示王，Q表示后，R表示车，B表示象，N表示马。描述一次移动，用棋子的字母和它的目的地坐标。一对这样的移动表示一个回合（白方先下），例如，棋谱2. Nf3 Nc6表明在棋局的第二回合，白方将马移动到f3，黑方将马移动到c6。

代数记谱法还有更多内容，但要点是你可以用它无二义地描述象棋游戏，不需要站在棋盘前。你的对手甚至可以在世界的另一边！实际上，如果你的记忆力很好，甚至不需要物理的棋具：只需要阅读寄来的棋子移动，更新心里想的棋盘。

计算机有很好的记忆力。现在计算机上的程序，很容易存储几百万个像'2. Nf3 Nc6'这样的字符串。这就是为什么计算机不用物理棋盘就能下象棋。它们用数据建模来表示棋盘，你可以编写代码来使用这个模型。

这里就可以用到列表和字典。可以用它们对真实世界建模，例如棋盘。作为第一个例子，我们将使用比国际象棋简单一点的游戏：井字棋。

### 5.3.1 井字棋盘井字棋盘看起来像一个大的井字符号（#），有9个空格，可以包含X、O或空。要用字典表示棋盘，可以为每个空格分配一个字符串键，如图5-2所示。

图5-2 井字棋盘的空格和它们对应的键可以用字符串值来表示，棋盘上每个空格有什么：'X'、'O'或' '（空格字符）。因此，需要存储9个字符串。可以用一个字典来做这事。带有键'top-R'的字符串表示右上角，带有键'low-L'的字符串表示左下角，带有键'mid-M'的字符串表示中间，以此类推。

这个字典就是表示井字棋盘的数据结构。将这个字典表示的棋盘保存在名为theBoard的变量中。打开一个文件编辑器窗口，输入以下代码，并保存为ticTacToe.py：theBoard = {'top-L': ' ', 'top-M': ' ', 'top-R': ' ', 'mid-L': ' ', 'mid-M': ' ', 'mid-R': ' ', 'low-L': ' ', 'low-M': ' ', 'low-R': ' '}

保存在theBoard变量中的数据结构，表示了图5-3中的井字棋盘。

图5-3 一个空的井字棋盘因为theBoard变量中每个键的值都是单个空格字符，所以这个字典表示一个完全干净的棋盘。如果玩家X选择了中间的空格，就可以用下面这个字典来表示棋盘：theBoard = {'top-L': ' ', 'top-M': ' ', 'top-R': ' ', 'mid-L': ' ', 'mid-M': 'X', 'mid-R': ' ', 'low-L': ' ', 'low-M': ' ', 'low-R': ' '}

theBoard变量中的数据结构现在表示图5-4中的井字棋盘。

图5-4 第一着一个玩家O获胜的棋盘上，他将O横贯棋盘的顶部，看起来像这样：theBoard = {'top-L': 'O', 'top-M': 'O', 'top-R': 'O', 'mid-L': 'X', 'mid-M': 'X', 'mid-R': ' ', 'low-L': ' ', 'low-M': ' ', 'low-R': 'X'}

theBoard变量中的数据结构现在表示图5-5中的井字棋盘。

图5-5 玩家O获胜当然，玩家只看到打印在屏幕上的内容，而不是变量的内容。让我们创建一个函数，将棋盘字典打印到屏幕上。将下面代码添加到ticTacToe.py（新代码是黑体的）：theBoard = {'top-L': ' ', 'top-M': ' ', 'top-R': ' ', 'mid-L': ' ', 'mid-M': ' ', 'mid-R': ' ', 'low-L': ' ', 'low-M': ' ', 'low-R': ' '} def printBoard(board): print(board['top-L'] + '|' + board['top-M'] + '|' + board['top-R']) print('-+-+-') print(board['mid-L'] + '|' + board['mid-M'] + '|' + board['mid-R']) print('-+-+-') print(board['low-L'] + '|' + board['low-M'] + '|' + board['low-R'])printBoard(theBoard)

运行这个程序时，printBoard()将打印出空白井字棋盘。| | -+-+- | | -+-+- | |

printBoard()函数可以处理传入的任何井字棋数据结构。尝试将代码改成以下的样子：theBoard = {'top-L': 'O', 'top-M': 'O', 'top-R': 'O', 'mid-L': 'X', 'mid-M':'X', 'mid-R': ' ', 'low-L': ' ', 'low-M': ' ', 'low-R': 'X'} def printBoard(board): print(board['top-L'] + '|' + board['top-M'] + '|' + board['top-R']) print('-+-+-') print(board['mid-L'] + '|' + board['mid-M'] + '|' + board['mid-R']) print('-+-+-') print(board['low-L'] + '|' + board['low-M'] + '|' + board['low-R']) printBoard(theBoard)

现在运行该程序，新棋盘将打印在屏幕上。O|O|O -+-+- X|X| -+-+- | |X

因为你创建了一个数据结构来表示井字棋盘，编写了printBoard()中的代码来解释该数据结构，所以就有了一个程序，对井字棋盘进行了"建模"。也可以用不同的方式组织数据结构（例如，使用'TOP-LEFT'这样的键来代替'top-L'），但只要代码能处理你的数据结构，就有了正确工作的程序。

例如，printBoard()函数预期井字棋数据结构是一个字典，包含所有9个空格的键。假如传入的字典缺少'mid-L'键，程序就不能工作了。O|O|O -+-+- Traceback (most recent call last): File "ticTacToe.py", line 10, in <module> printBoard(theBoard) File "ticTacToe.py", line 6, in printBoard print(board['mid-L'] + '|' + board['mid-M'] + '|' + board['mid-R']) KeyError: 'mid-L'

现在让我们添加代码，允许玩家输入他们的着法。修改ticTacToe.py程序如下所示： theBoard = {'top-L': ' ', 'top-M': ' ', 'top-R': ' ', 'mid-L': ' ', 'mid-M': '', 'mid-R': ' ', 'low-L': ' ', 'low-M': ' ', 'low-R': ' '} def printBoard(board): print(board['top-L'] + '|' + board['top-M'] + '|' + board['top-R']) print('-+-+-') print(board['mid-L'] + '|' + board['mid-M'] + '|' + board['mid-R']) print('-+-+-') print(board['low-L'] + '|' + board['low-M'] + '|' + board['low-R']) turn = 'X'for i in range(9): 1. printBoard(theBoard)print('Turn for ' + turn + '. Move on which space?') 2. move = input() 3. theBoard[move] = turn 4. if turn == 'X':turn = 'O'else:turn = 'X' printBoard(theBoard)

新的代码在每一步新的着法之前，打印出棋盘1. ，获取当前棋手的着法2. ，相应地更新棋盘3. ，然后改变当前棋手4. ，进入到下一着。

运行该程序，它看起来像这样： | | -+-+- | | -+-+- | | Turn for X. Move on which space? mid-M | | -+-+- |X| -+-+- | | Turn for O. Move on which space? low-L | | -+-+- |X| -+-+- O| | --_snip_-- O|O|X -+-+- X|X|O -+-+- O| |X Turn for X. Move on which space? low-M O|O|X -+-+- X|X|O -+-+- O|X|X

这不是一个完整的井字棋游戏（例如，它并不检查玩家是否获胜），但这已足够展示如何在程序中使用数据结构。

注意如果你很好奇，完整的井字棋程序的源代码在网上有介绍，网址是http://nostarch.com/automatestuff/ 。

### 5.3.2 嵌套的字典和列表对井字棋盘建模相当简单：棋盘只需要一个字典，包含9个键值对。当你对复杂的事物建模时，可能发现字典和列表中需要包含其他字典和列表。列表适用于包含一组有序的值，字典适合于包含关联的键与值。例如，下面的程序使用字典包含其他字典，用于记录谁为野餐带来了什么食物。totalBrought()函数可以读取这个数据结构，计算所有客人带来的食物的总数。 allGuests = {'Alice': {'apples': 5, 'pretzels': 12}, 'Bob': {'ham sandwiches': 3, 'apples': 2}, 'Carol': {'cups': 3, 'apple pies': 1}} def totalBrought(guests, item): numBrought = 0 1. for k, v in guests.items(): 2. numBrought = numBrought + v.get(item, 0) return numBrought print('Number of things being brought:') print(' - Apples ' + str(totalBrought(allGuests, 'apples'))) print(' - Cups ' + str(totalBrought(allGuests, 'cups'))) print(' - Cakes ' + str(totalBrought(allGuests, 'cakes'))) print(' - Ham Sandwiches ' + str(totalBrought(allGuests, 'ham sandwiches'))) print(' - Apple Pies ' + str(totalBrought(allGuests, 'apple pies')))

在totalBrought()函数中，for循环迭代guests中的每个键值对1. 。在这个循环里，客人的名字字符串赋给k，他们带来的野餐食物的字典赋给v。如果食物参数是字典中存在的键，它的值（数量）就添加到numBrought2. 。如果它不是键，get()方法就返回0，添加到numBrought。

该程序的输出像这样：Number of things being brought: - Apples 7 - Cups 3 - Cakes 0 - Ham Sandwiches 3 - Apple Pies 1

这似乎对一个非常简单的东西建模，你可能认为不需要费事去写一个程序来做到这一点。但是要认识到，这个函数totalBrought()可以轻易地处理一个字典，其中包含数千名客人，每个人都带来了"数千种"不同的野餐食物。这样用这种数据结构来保存信息，并使用totalBrought()函数，就会节约大量的时间！

你可以用自己喜欢的任何方法，用数据结构对事物建模，只要程序中其他代码能够正确处理这个数据模型。在刚开始编程时，不需要太担心数据建模的"正确"方式。随着经验增加，你可能会得到更有效的模型，但重要的是，该数据模型符合程序的需要。

## 5.4 小结在本章中，你学习了字典的所有相关知识。列表和字典是这样的值，它们可以包含多个值，包括其他列表和字典。字典是有用的，因为你可以把一些项（键）映射到另一些项（值），它不像列表，只包含一系列有序的值。字典中的值是通过方括号访问的，像列表一样。字典不是只能使用整数下标，而是可以用各种数据类型作为键：整型、浮点型、字符串或元组。通过将程序中的值组织成数据结构，你可以创建真实世界事物的模型。井字棋盘就是这样一个例子。

这就介绍了Python编程的所有基本概念！在本书后面的部分，你将继续学习一些新概念，但现在你已学习了足够多的内容，可以开始编写一些有用的程序，让一些任务自动化。你可能不觉得自己有足够的Python知识，来实现页面下载、更新电子表格，或发送文本消息。但这就是Python模块要干的事！这些模块由其他程序员编写，提供了一些函数，让这些事情变得容易。所以让我们学习如何编写真正的程序，实现有用的自动化任务。

## 5.5 习题

1．空字典的代码是怎样的？

2．一个字典包含键'fow'和值42，看起来是怎样的？

3．字典和列表的主要区别是什么？

4．如果spam是{'bar': 100}，你试图访问spam['foo']，会发生什么？

5．如果一个字典保存在spam中，表达式'cat' in spam和'cat' in spam.keys()之间的区别是什么？

6．如果一个字典保存在变量中，表达式'cat' in spam和'cat' in spam.values()之间的区别是什么？

7．下面代码的简洁写法是什么？if 'color' not in spam: spam['color'] = 'black'

8．什么模块和函数可以用于"漂亮打印"字典值？

## 5.6 实践项目作为实践，编程完成下列任务。

### 5.6.1 好玩游戏的物品清单你在创建一个好玩的视频游戏。用于对玩家物品清单建模的数据结构是一个字典。其中键是字符串，描述清单中的物品，值是一个整型值，说明玩家有多少该物品。例如，字典值{'rope': 1, 'torch': 6, 'gold coin': 42, 'dagger': 1, 'arrow': 12}意味着玩家有1条绳索、6个火把、42枚金币等。

写一个名为displayInventory()的函数，它接受任何可能的物品清单，并显示如下：Inventory: 12 arrow 42 gold coin 1 rope 6 torch 1 dagger Total number of items: 62

提示你可以使用for循环，遍历字典中所有的键。

# inventory.py stuff = {'rope': 1, 'torch': 6, 'gold coin': 42, 'dagger': 1, 'arrow': 12} def displayInventory(inventory): print("Inventory:") item_total = 0 for k, v in inventory.items(): print(str(v) + ' ' + k) item_total += v print("Total number of items: " + str(item_total)) displayInventory(stuff)

### 5.6.2 列表到字典的函数，针对好玩游戏物品清单假设征服一条龙的战利品表示为这样的字符串列表：dragonLoot = ['gold coin', 'dagger', 'gold coin', 'gold coin', 'ruby']

写一个名为addToInventory(inventory, addedItems)的函数，其中inventory参数是一个字典，表示玩家的物品清单（像前面项目一样），addedItems参数是一个列表，就像dragonLoot。

addToInventory()函数应该返回一个字典，表示更新过的物品清单。请注意，列表可以包含多个同样的项。你的代码看起来可能像这样：def addToInventory(inventory, addedItems): # your code goes here inv = {'gold coin': 42, 'rope': 1} dragonLoot = ['gold coin', 'dagger', 'gold coin', 'gold coin', 'ruby'] inv = addToInventory(inv, dragonLoot) displayInventory(inv)

前面的程序（加上前一个项目中的displayInventory()函数）将输出如下：Inventory: 45 gold coin 1 rope 1 ruby 1 dagger Total number of items: 48

# 第二部分自动化任务

# 第7章模式匹配与正则表达式你可能熟悉文本查找，即按下Ctrl-F，输入你要查找的词。"正则表达式"更进一步，它们让你指定要查找的"模式"。你也许不知道一家公司的准确电话号码，但如果你住在美国或加拿大，你就知道它有3位数字，然后是一个短横线，然后是4位数字（有时候以3位区号开始）。因此作为一个人，你看到一个电话号码就知道：415-555-1234是电话号码，但4,155,551,234不是。

正则表达式很有用，但如果不是程序员，很少会有人了解它，尽管大多数现代文本编辑器和文字处理器（诸如微软的Word或OpenOffice），都有查找和查找替换功能，可以根据正则表达式查找。正则表达式可以节约大量时间，不仅适用于软件用户，也适用于程序员。实际上，技术作家Cory Doctorow声称，甚至应该在教授编程之前，先教授正则表达式：

"知道[正则表达式]可能意味着用3步解决一个问题，而不是用3000步。如果你是一个技术怪侠，别忘了你用几次击键就能解决的问题，其他人需要数天的烦琐工作才能解决，而且他们容易犯错。" [1]

在本章中，你将从编写一个程序开始，先不用正则表达式来寻找文本模式。然后再看看，使用正则表达式让代码变得多么简洁。我将展示用正则表达式进行基本匹配，然后转向一些更强大的功能，诸如字符串替换，以及创建你自己的字符类型。最后，在本章末尾，你将编写一个程序，从一段文本中自动提取电话号码和E-mail地址。

## 7.1 不用正则表达式来查找文本模式假设你希望在字符串中查找电话号码。你知道模式：3个数字，一个短横线，3个数字，一个短横线，再是4个数字。例如：415-555-4242。

假定我们用一个名为isPhoneNumber()的函数，来检查字符串是否匹配模式，它返回True或False。打开一个新的文件编辑器窗口，输入以下代码，然后保存为isPhoneNumber.py： def isPhoneNumber(text): 1. if len(text) != 12: return False for i in range(0, 3): 2. if not text[i].isdecimal(): return False 3. if text[3] != '-': return False for i in range(4, 7): 4. if not text[i].isdecimal(): return False 5. if text[7] != '-': return False for i in range(8, 12): 6. if not text[i].isdecimal(): return False 7. return True print('415-555-4242 is a phone number:') print(isPhoneNumber('415-555-4242')) print('Moshi moshi is a phone number:') print(isPhoneNumber('Moshi moshi'))

运行该程序，输出看起来像这样：415-555-4242 is a phone number: True Moshi moshi is a phone number: False

isPhoneNumber()函数的代码进行几项检查，看看text中的字符串是不是有效的电话号码。如果其中任意一项检查失败，函数就返回False。代码首先检查该字符串是否刚好有12个字符1. 。然后它检查区号（就是text中的前3个字符）是否只包含数字2. 。函数剩下的部分检查该字符串是否符合电话号码的模式：号码必须在区号后出现第一个短横线3. ，3个数字4. ，然后是另一个短横线5. ，最后是4个数字6. 。如果程序执行通过了所有的检查，它就返回True7. 。

用参数'415-555-4242'调用isPhoneNumber()将返回真。用参数'Moshi moshi'调用isPhoneNumber()将返回假，第一项测试失败了，因为不是12个字符。

必须添加更多代码，才能在更长的字符串中寻找这种文本模式。用下面的代码，替代isPhoneNumber.py中最后4个print()函数调用： message = 'Call me at 415-555-1011 tomorrow. 415-555-9999 is my office.' for i in range(len(message)): 1. chunk = message[i:i+12] 2. if isPhoneNumber(chunk): print('Phone number found: ' + chunk) print('Done')

该程序运行时，输出看起来像这样：Phone number found: 415-555-1011 Phone number found: 415-555-9999 Done

在for循环的每一次迭代中，取自message的一段新的12个字符被赋给变量chunk1. 。例如，在第一次迭代，i是0，chunk被赋值为message[0:12]（即字符串'Call me at 4'）。在下一次迭代，i是1，chunk被赋值为message[1:13]（字符串'all me at 41'）。

将chunk传递给isPhoneNumber()，看看它是否符合电话号码的模式2. 。如果符合，就打印出这段文本。

继续遍历message，最终chunk中的12个字符会是一个电话号码。该循环遍历了整个字符串，测试了每一段12个字符，打印出所有满足isPhoneNumber()的chunk。当我们遍历完message，就打印出Done。

在这个例子中，虽然message中的字符串很短，但它也可能包含上百万个字符，程序运行仍然不需要一秒钟。使用正则表达式查找电话号码的类似程序，运行也不会超过一秒钟，但用正则表达式编写这类程序会快得多。

## 7.2 用正则表达式查找文本模式前面的电话号码查找程序能工作，但它使用了很多代码，做的事却有限：isPhoneNumber()函数有17行，但只能查找一种电话号码模式。像415.555.4242或(415) 555-4242这样的电话号码格式，该怎么办呢？如果电话号码有分机，例如415-555-4242 x99，该怎么办呢？isPhoneNumber()函数在验证它们时会失败。你可以添加更多的代码来处理额外的模式，但还有更简单的方法。

正则表达式，简称为regex，是文本模式的描述方法。例如，\d 是一个正则表达式，表示一位数字字符，即任何一位 0 到 9 的数字。Python 使用正则表达式\d\d\d-\d\d\d-\d\d\d\d，来匹配前面isPhoneNumber()函数匹配的同样文本：3 个数字、一个短横线、3 个数字、一个短横线、4 个数字。所有其他字符串都不能匹配\d\d\d-\d\d\d-\d\d\d\d正则表达式。

但正则表达式可以复杂得多。例如，在一个模式后加上花括号包围的3（{3}），就是说，"匹配这个模式3次"。所以较短的正则表达式\d{3}-\d{3}-\d{4}，也匹配正确的电话号码格式。

### 7.2.1 创建正则表达式对象

Python中所有正则表达式的函数都在re模块中。在交互式环境中输入以下代码，导入该模块：>>> import re

注意本章后面的大多数例子都需要re模块，所以要记得在你写的每个脚本开始处导入它，或重新启动IDLE时。否则，就会遇到错误消息NameError: name 're' is not defined。

向re.compile()传入一个字符串值，表示正则表达式，它将返回一个Regex模式对象（或者就简称为Regex对象）。

要创建一个Regex对象来匹配电话号码模式，就在交互式环境中输入以下代码（回忆一下，\d表示"一个数字字符"，\d\d\d-\d\d\d-\d\d\d\d是正确电话号码模式的正则表达式）。>>> phoneNumRegex = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d')

现在phoneNumRegex变量包含了一个Regex对象。

### 7.2.2 匹配Regex对象

Regex对象的search()方法查找传入的字符串，寻找该正则表达式的所有匹配。如果字符串中没有找到该正则表达式模式，search()方法将返回None。如果找到了该模式，search()方法将返回一个Match对象。Match对象有一个group()方法，它返回被查找字符串中实际匹配的文本（稍后我会解释分组）。例如，在交互式环境中输入以下代码：>>> phoneNumRegex = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d') >>> mo = phoneNumRegex.search('My number is 415-555-4242.') >>> print('Phone number found: ' + mo.group()) Phone number found: 415-555-4242

变量名mo是一个通用的名称，用于Match对象。这个例子可能初看起来有点复杂，但它比前面的isPhoneNumber.py程序要短很多，并且做的事情一样。

这里，我们将期待的模式传递给re.compile()，并将得到的Regex对象保存在phoneNumRegex中。然后我们在phoneNumRegex上调用search()，向它传入想查找的字符串。查找的结果保存在变量mo中。在这个例子里，我们知道模式会在这个字符串中找到，所以我们知道会返回一个Match对象。知道mo包含一个Match对象，而不是空值None，我们就可以在mo变量上调用group()，返回匹配的结果。将mo.group()写在打印语句中，显示出完整的匹配，即415-555-4242。

向re.compile()传递原始字符串回忆一下，Python中转义字符使用倒斜杠（\）。字符串'\n'表示一个换行字符，而不是倒斜杠加上一个小写的n。你需要输入转义字符\，才能打印出一个倒斜杠。所以'\n'表示一个倒斜杠加上一个小写的n。但是，通过在字符串的第一个引号之前加上r，可以将该字符串标记为原始字符串，它不包括转义字符。

因为正则表达式常常使用倒斜杠，向re.compile()函数传入原始字符串就很方便，而不是输入额外得到斜杠。输入r'\d\d\d-\d\d\d-\d\d\d\d'，比输入'\d\d\d-\d\d\d-\d\d\d\d'要容易得多。

### 7.2.3 正则表达式匹配复习虽然在Python中使用正则表达式有几个步骤，但每一步都相当简单。

1．用import re导入正则表达式模块。

2．用re.compile()函数创建一个Regex对象（记得使用原始字符串）。

3．向Regex对象的search()方法传入想查找的字符串。它返回一个Match对象。

4．调用Match对象的group()方法，返回实际匹配文本的字符串。

注意虽然我鼓励你在交互式环境中输入示例代码,但你也应该利用基于网页的正则表达式测试程序。它可以向你清楚地展示，一个正则表达式如何匹配输入的一段文本。我推荐的测试程序位于http://regexpal.com/ 。

## 7.3 用正则表达式匹配更多模式既然你已知道用Python创建和查找正则表达式对象的基本步骤，就可以尝试一些更强大的模式匹配功能了。

### 7.3.1 利用括号分组假定想要将区号从电话号码中分离。添加括号将在正则表达式中创建"分组"：(\d\d\d)-(\d\d\d-\d\d\d\d)。然后可以使用group()匹配对象方法，从一个分组中获取匹配的文本。

正则表达式字符串中的第一对括号是第1组。第二对括号是第2组。向group()匹配对象方法传入整数1或2，就可以取得匹配文本的不同部分。向group()方法传入0或不传入参数，将返回整个匹配的文本。在交互式环境中输入以下代码：>>> phoneNumRegex = re.compile(r'(\d\d\d)-(\d\d\d-\d\d\d\d)') >>> mo = phoneNumRegex.search('My number is 415-555-4242.') >>> mo.group(1) '415' >>> mo.group(2) '555-4242' >>> mo.group(0) '415-555-4242' >>> mo.group() '415-555-4242'

如果想要一次就获取所有的分组，请使用groups()方法，注意函数名的复数形式。>>> mo.groups() ('415', '555-4242') >>> areaCode, mainNumber = mo.groups() >>> print(areaCode) 415 >>> print(mainNumber) 555-4242

因为mo.groups()返回多个值的元组，所以你可以使用多重赋值的技巧，每个值赋给一个独立的变量，就像前面的代码行：areaCode, mainNumber = mo.groups()。

括号在正则表达式中有特殊的含义，但是如果你需要在文本中匹配括号，怎么办？例如，你要匹配的电话号码，可能将区号放在一对括号中。在这种情况下，就需要用倒斜杠对(和)进行字符转义。在交互式环境中输入以下代码：>>> phoneNumRegex = re.compile(r'(\(\d\d\d\)) (\d\d\d-\d\d\d\d)') >>> mo = phoneNumRegex.search('My phone number is (415) 555-4242.') >>> mo.group(1) '(415)' >>> mo.group(2) '555-4242'

传递给re.compile()的原始字符串中，(和)转义字符将匹配实际的括号字符。

### 7.3.2 用管道匹配多个分组字符|称为"管道"。希望匹配许多表达式中的一个时，就可以使用它。例如，正则表达式r'Batman|Tina Fey'将匹配'Batman'或'Tina Fey'。

如果Batman和Tina Fey都出现在被查找的字符串中，第一次出现的匹配文本，将作为Match对象返回。在交互式环境中输入以下代码：>>> heroRegex = re.compile (r'Batman|Tina Fey') >>> mo1 = heroRegex.search('Batman and Tina Fey.') >>> mo1.group() 'Batman' >>> mo2 = heroRegex.search('Tina Fey and Batman.') >>> mo2.group() 'Tina Fey'

注意利用findall()方法，可以找到"所有"匹配的地方。这在7.5节"findall()方法"中讨论。

也可以使用管道来匹配多个模式中的一个，作为正则表达式的一部分。例如，假设你希望匹配'Batman'、'Batmobile'、'Batcopter'和'Batbat'中任意一个。因为所有这些字符串都以Bat开始，所以如果能够只指定一次前缀，就很方便。这可以通过括号实现。在交互式环境中输入以下代码：>>> batRegex = re.compile(r'Bat(man|mobile|copter|bat)') >>> mo = batRegex.search('Batmobile lost a wheel') >>> mo.group() 'Batmobile' >>> mo.group(1) 'mobile'

方法调用mo.group()返回了完全匹配的文本'Batmobile'，而mo.group(1)只是返回第一个括号分组内匹配的文本'mobile'。通过使用管道字符和分组括号，可以指定几种可选的模式，让正则表达式去匹配。

如果需要匹配真正的管道字符，就用倒斜杠转义，即|。

### 7.3.3 用问号实现可选匹配有时候，想匹配的模式是可选的。就是说，不论这段文本在不在，正则表达式都会认为匹配。字符?表明它前面的分组在这个模式中是可选的。例如，在交互式环境中输入以下代码：>>> batRegex = re.compile(r'Bat(wo)?man') >>> mo1 = batRegex.search('The Adventures of Batman') >>> mo1.group() 'Batman' >>> mo2 = batRegex.search('The Adventures of Batwoman') >>> mo2.group() 'Batwoman'

正则表达式中的(wo)?部分表明，模式wo是可选的分组。该正则表达式匹配的文本中，wo将出现零次或一次。这就是为什么正则表达式既匹配'Batwoman'，又匹配'Batman'。

利用前面电话号码的例子，你可以让正则表达式寻找包含区号或不包含区号的电话号码。在交互式环境中输入以下代码：>>> phoneRegex = re.compile(r'(\d\d\d-)?\d\d\d-\d\d\d\d') >>> mo1 = phoneRegex.search('My number is 415-555-4242') >>> mo1.group() '415-555-4242' >>> mo2 = phoneRegex.search('My number is 555-4242') >>> mo2.group() '555-4242'

你可以认为?是在说，"匹配这个问号之前的分组零次或一次"。

如果需要匹配真正的问号字符，就使用转义字符\?。

### 7.3.4 用星号匹配零次或多次

*（称为星号）意味着"匹配零次或多次"，即星号之前的分组，可以在文本中出现任意次。它可以完全不存在，或一次又一次地重复。让我们再来看看Batman的例子。>>> batRegex = re.compile(r'Bat(wo)*man') >>> mo1 = batRegex.search('The Adventures of Batman') >>> mo1.group() 'Batman' >>> mo2 = batRegex.search('The Adventures of Batwoman') >>> mo2.group() 'Batwoman' >>> mo3 = batRegex.search('The Adventures of Batwowowowoman') >>> mo3.group() 'Batwowowowoman'

对于'Batman'，正则表达式的(wo)部分匹配wo的零个实例。对于'Batwoman'，(wo) 匹配wo的一个实例。对于'Batwowowowoman'，(wo)*匹配wo的4个实例。

如果需要匹配真正的星号字符，就在正则表达式的星号字符前加上倒斜杠，即*。

### 7.3.5 用加号匹配一次或多次

*意味着"匹配零次或多次"，+（加号）则意味着"匹配一次或多次"。星号不要求分组出现在匹配的字符串中，但加号不同，加号前面的分组必须"至少出现一次"。这不是可选的。在交互式环境中输入以下代码，把它和前一节的星号正则表达式进行比较：>>> batRegex = re.compile(r'Bat(wo)+man') >>> mo1 = batRegex.search('The Adventures of Batwoman') >>> mo1.group() 'Batwoman' >>> mo2 = batRegex.search('The Adventures of Batwowowowoman') >>> mo2.group() 'Batwowowowoman' >>> mo3 = batRegex.search('The Adventures of Batman') >>> mo3 == None True

正则表达式Bat(wo)+man不会匹配字符串'The Adventures of Batman'，因为加号要求wo至少出现一次。

如果需要匹配真正的加号字符，在加号前面加上倒斜杠实现转义：+。

### 7.3.6 用花括号匹配特定次数如果想要一个分组重复特定次数，就在正则表达式中该分组的后面，跟上花括号包围的数字。例如，正则表达式(Ha){3}将匹配字符串'HaHaHa'，但不会匹配'HaHa'，因为后者只重复了(Ha)分组两次。

除了一个数字，还可以指定一个范围，即在花括号中写下一个最小值、一个逗号和一个最大值。例如，正则表达式(Ha){3,5}将匹配'HaHaHa'、'HaHaHaHa'和'HaHaHaHaHa'。

也可以不写花括号中的第一个或第二个数字，不限定最小值或最大值。例如，(Ha){3,}将匹配3次或更多次实例，(Ha){,5}将匹配0到5次实例。花括号让正则表达式更简短。这两个正则表达式匹配同样的模式：(Ha){3} (Ha)(Ha)(Ha)

这两个正则表达式也匹配同样的模式：(Ha){3,5} ((Ha)(Ha)(Ha))|((Ha)(Ha)(Ha)(Ha))|((Ha)(Ha)(Ha)(Ha)(Ha))

在交互式环境中输入以下代码：>>> haRegex = re.compile(r'(Ha){3}') >>> mo1 = haRegex.search('HaHaHa') >>> mo1.group() 'HaHaHa' >>> mo2 = haRegex.search('Ha') >>> mo2 == None True

这里，(Ha){3}匹配'HaHaHa'，但不匹配'Ha'。因为它不匹配'Ha'，所以search()返回None。

## 7.4 贪心和非贪心匹配在字符串'HaHaHaHaHa'中，因为(Ha){3,5}可以匹配3个、4个或5个实例，你可能会想，为什么在前面花括号的例子中，Match对象的group()调用会返回'HaHaHaHaHa'，而不是更短的可能结果。毕竟，'HaHaHa'和'HaHaHaHa'也能够有效地匹配正则表达式(Ha){3,5}。

Python的正则表达式默认是"贪心"的，这表示在有二义的情况下，它们会尽可能匹配最长的字符串。花括号的"非贪心"版本匹配尽可能最短的字符串，即在结束的花括号后跟着一个问号。

在交互式环境中输入以下代码，注意在查找相同字符串时，花括号的贪心形式和非贪心形式之间的区别：>>> greedyHaRegex = re.compile(r'(Ha){3,5}') >>> mo1 = greedyHaRegex.search('HaHaHaHaHa') >>> mo1.group() 'HaHaHaHaHa' >>> nongreedyHaRegex = re.compile(r'(Ha){3,5}?') >>> mo2 = nongreedyHaRegex.search('HaHaHaHaHa') >>> mo2.group() 'HaHaHa'

请注意，问号在正则表达式中可能有两种含义：声明非贪心匹配或表示可选的分组。这两种含义是完全无关的。

## 7.5 findall()方法除了search方法外，Regex对象也有一个findall()方法。search()将返回一个Match对象，包含被查找字符串中的"第一次"匹配的文本，而findall()方法将返回一组字符串，包含被查找字符串中的所有匹配。为了看看search()返回的Match对象只包含第一次出现的匹配文本，请在交互式环境中输入以下代码：>>> phoneNumRegex = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d') >>> mo = phoneNumRegex.search('Cell: 415-555-9999 Work: 212-555-0000') >>> mo.group() '415-555-9999'

另一方面，findall()不是返回一个Match对象，而是返回一个字符串列表，只要在正则表达式中没有分组。列表中的每个字符串都是一段被查找的文本，它匹配该正则表达式。在交互式环境中输入以下代码：>>> phoneNumRegex = re.compile(r'\d\d\d-\d\d\d-\d\d\d\d') # has no groups >>> phoneNumRegex.findall('Cell: 415-555-9999 Work: 212-555-0000') ['415-555-9999', '212-555-0000']

如果在正则表达式中有分组，那么findall将返回元组的列表。每个元组表示一个找到的匹配，其中的项就是正则表达式中每个分组的匹配字符串。为了看看findall()的效果，请在交互式环境中输入以下代码（请注意，被编译的正则表达式现在有括号分组）：>>> phoneNumRegex = re.compile(r'(\d\d\d)-(\d\d\d)-(\d\d\d\d)') # has groups >>> phoneNumRegex.findall('Cell: 415-555-9999 Work: 212-555-0000') [('415', '555', '1122'), ('212', '555', '0000')]

作为findall()方法的返回结果的总结，请记住下面两点：

1．如果调用在一个没有分组的正则表达式上，例如\d\d\d-\d\d\d-\d\d\d\d，方法findall()将返回一个匹配字符串的列表，例如['415-555-9999', '212-555-0000']。

2．如果调用在一个有分组的正则表达式上，例如(\d\d\d)-(\d\d\d)-(\d\d\d\d)，方法findall()将返回一个字符串的元组的列表（每个分组对应一个字符串），例如[('415', '555', '1122'), ('212', '555', '0000')]。

## 7.6 字符分类在前面电话号码正则表达式的例子中，你知道\d 可以代表任何数字。也就是说，\d是正则表达式(0|1|2|3|4|5|6|7|8|9)的缩写。有许多这样的"缩写字符分类"，如表7-1所示。

表7-1 常用字符分类的缩写代码缩写字符分类表示

\d

0到9的任何数字

\D

除0到9的数字以外的任何字符

\w

任何字母、数字或下划线字符（可以认为是匹配"单词"字符）

\W

除字母、数字和下划线以外的任何字符

\s

空格、制表符或换行符（可以认为是匹配"空白"字符）

\S

除空格、制表符和换行符以外的任何字符字符分类对于缩短正则表达式很有用。字符分类[0-5]只匹配数字0到5，这比输入(0|1|2|3|4|5)要短很多。

例如，在交互式环境中输入以下代码：>>> xmasRegex = re.compile(r'\d+\s\w+') >>> xmasRegex.findall('12 drummers, 11 pipers, 10 lords, 9 ladies, 8 maids, 7swans, 6 geese, 5 rings, 4 birds, 3 hens, 2 doves, 1 partridge') ['12 drummers', '11 pipers', '10 lords', '9 ladies', '8 maids', '7 swans', '6 geese', '5 rings', '4 birds', '3 hens', '2 doves', '1 partridge']

正则表达式\d+\s\w+匹配的文本有一个或多个数字(\d+)，接下来是一个空白字符(\s)，接下来是一个或多个字母/数字/下划线字符(\w+)。findall()方法将返回所有匹配该正则表达式的字符串，放在一个列表中。

## 7.7 建立自己的字符分类有时候你想匹配一组字符，但缩写的字符分类（\d、\w、\s等）太宽泛。你可以用方括号定义自己的字符分类。例如，字符分类[aeiouAEIOU]将匹配所有元音字符，不论大小写。在交互式环境中输入以下代码：>>> vowelRegex = re.compile(r'[aeiouAEIOU]') >>> vowelRegex.findall('RoboCop eats baby food. BABY FOOD.') ['o', 'o', 'o', 'e', 'a', 'a', 'o', 'o', 'A', 'O', 'O']

也可以使用短横表示字母或数字的范围。例如，字符分类[a-zA-Z0-9]将匹配所有小写字母、大写字母和数字。

请注意，在方括号内，普通的正则表达式符号不会被解释。这意味着，你不需要前面加上倒斜杠转义.、*、?或()字符。例如，字符分类将匹配数字0到5和一个句点。你不需要将它写成[0-5.]。

通过在字符分类的左方括号后加上一个插入字符（^），就可以得到"非字符类"。非字符类将匹配不在这个字符类中的所有字符。例如，在交互式环境中输入以下代码：>>> consonantRegex = re.compile(r'[^aeiouAEIOU]') >>> consonantRegex.findall('RoboCop eats baby food. BABY FOOD.') ['R', 'b', 'c', 'p', ' ', 't', 's', ' ', 'b', 'b', 'y', ' ', 'f', 'd', '.', ' ', 'B', 'B', 'Y', ' ', 'F', 'D', '.']

现在，不是匹配所有元音字符，而是匹配所有非元音字符。

## 7.8 插入字符和美元字符可以在正则表达式的开始处使用插入符号（^），表明匹配必须发生在被查找文本开始处。类似地，可以在正则表达式的末尾加上美元符号（$），表示该字符串必须以这个正则表达式的模式结束。可以同时使用^和$，表明整个字符串必须匹配该模式，也就是说，只匹配该字符串的某个子集是不够的。

例如，正则表达式r'^Hello'匹配以'Hello'开始的字符串。在交互式环境中输入以下代码：>>> beginsWithHello = re.compile(r'^Hello') >>> beginsWithHello.search('Hello world!') < _sre.SRE_Match object; span=(0, 5), match='Hello'> >>> beginsWithHello.search('He said hello.') == None True

正则表达式r'\d$'匹配以数字0到9结束的字符串。在交互式环境中输入以下代码：>>> endsWithNumber = re.compile(r'\d$') >>> endsWithNumber.search('Your number is 42') < _sre.SRE_Match object; span=(16, 17), match='2'> >>> endsWithNumber.search('Your number is forty two.') == None True

正则表达式r'^\d+$'匹配从开始到结束都是数字的字符串。在交互式环境中输入以下代码：>>> wholeStringIsNum = re.compile(r'^\d+$') >>> wholeStringIsNum.search('1234567890') < _sre.SRE_Match object; span=(0, 10), match='1234567890'> >>> wholeStringIsNum.search('12345xyz67890') == None True >>> wholeStringIsNum.search('12 34567890') == None True

前面交互式脚本例子中的最后两次search()调用表明，如果使用了^和$，那么整个字符串必须匹配该正则表达式。

我总是会混淆这两个符号的含义，所以我使用助记法"Carrots cost dollars"，提醒我插入符号在前面，美元符号在后面。

## 7.9 通配字符在正则表达式中，.（句点）字符称为"通配符"。它匹配除了换行之外的所有字符。例如，在交互式环境中输入以下代码：>>> atRegex = re.compile(r'.at') >>> atRegex.findall('The cat in the hat sat on the flat mat.') ['cat', 'hat', 'sat', 'lat', 'mat']

要记住，句点字符只匹配一个字符，这就是为什么在前面的例子中，对于文本flat，只匹配lat。要匹配真正的句点，就是用倒斜杠转义：.。

### 7.9.1 用点-星匹配所有字符有时候想要匹配所有字符串。例如，假定想要匹配字符串'First Name:'，接下来是任意文本，接下来是'Last Name:'，然后又是任意文本。可以用点-星（.*）表示"任意文本"。回忆一下，句点字符表示"除换行外所有单个字符"，星号字符表示"前面字符出现零次或多次"。

在交互式环境中输入以下代码：>>> nameRegex = re.compile(r'First Name: (.*) Last Name: (.*)') >>> mo = nameRegex.search('First Name: Al Last Name: Sweigart') >>> mo.group(1) 'Al' >>> mo.group(2) 'Sweigart'

点-星使用"贪心"模式：它总是匹配尽可能多的文本。要用"非贪心"模式匹配所有文本，就使用点-星和问号。像和大括号一起使用时那样，问号告诉Python用非贪心模式匹配。在交互式环境中输入以下代码，看看贪心模式和非贪心模式的区别：>>> nongreedyRegex = re.compile(r'<.*?>') >>> mo = nongreedyRegex.search(' for dinner.>') >>> mo.group() '< To serve man>' >>> greedyRegex = re.compile(r'<.*>') >>> mo = greedyRegex.search(' for dinner.>') >>> mo.group() '< To serve man> for dinner.>'

两个正则表达式都可以翻译成"匹配一个左尖括号，接下来是任意字符，接下来是一个右尖括号"。但是字符串'<To serve man> for dinner.>'对右肩括号有两种可能的匹配。在非贪心的正则表达式中，Python匹配最短可能的字符串：'<To serve man>'。在贪心版本中，Python匹配最长可能的字符串：'<To serve man> for dinner.>'。

### 7.9.2 用句点字符匹配换行点-星将匹配除换行外的所有字符。通过传入re.DOTALL作为re.compile()的第二个参数，可以让句点字符匹配所有字符，包括换行字符。

在交互式环境中输入以下代码：>>> noNewlineRegex = re.compile('.*') >>> noNewlineRegex.search('Serve the public trust.\nProtect the innocent.\nUphold the law.').group() 'Serve the public trust.' >>> newlineRegex = re.compile('.*', re.DOTALL) >>> newlineRegex.search('Serve the public trust.\nProtect the innocent.\nUphold the law.').group() 'Serve the public trust.\nProtect the innocent.\nUphold the law.'

正则表达式noNewlineRegex在创建时没有向re.compile()传入re.DOTALL，它将匹配所有字符，直到第一个换行字符。但是，newlineRegex在创建时向re.compile()传入了re.DOTALL，它将匹配所有字符。这就是为什么newlineRegex.search()调用匹配完整的字符串，包括其中的换行字符。

## 7.10 正则表达式符号复习本章介绍了许多表示法，所以这里快速复习一下学到的内容：

- ?匹配零次或一次前面的分组。

- *匹配零次或多次前面的分组。

- +匹配一次或多次前面的分组。

- {n}匹配n次前面的分组。

- {n,}匹配n次或更多前面的分组。

- {,m}匹配零次到m次前面的分组。

- {n,m}匹配至少n次、至多m次前面的分组。

- {n,m}?或*?或+?对前面的分组进行非贪心匹配。

- ^spam意味着字符串必须以spam开始。

- spam$意味着字符串必须以spam结束。

- .匹配所有字符，换行符除外。

- \d、\w和\s分别匹配数字、单词和空格。

- \D、\W和\S分别匹配出数字、单词和空格外的所有字符。

- [abc]匹配方括号内的任意字符（诸如a、b或c）。

- [^abc]匹配不在方括号内的任意字符。

## 7.11 不区分大小写的匹配通常，正则表达式用你指定的大小写匹配文本。例如，下面的正则表达式匹配完全不同的字符串：>>> regex1 = re.compile('RoboCop') >>> regex2 = re.compile('ROBOCOP') >>> regex3 = re.compile('robOcop') >>> regex4 = re.compile('RobocOp')

但是，有时候你只关心匹配字母，不关心它们是大写或小写。要让正则表达式不区分大小写，可以向re.compile()传入re.IGNORECASE或re.I，作为第二个参数。在交互式环境中输入以下代码：>>> robocop = re.compile(r'robocop', re.I) >>> robocop.search('RoboCop is part man, part machine, all cop.').group() 'RoboCop' >>> robocop.search('ROBOCOP protects the innocent.').group() 'ROBOCOP' >>> robocop.search('Al, why does your programming book talk about robocop so much?').group() 'robocop'

## 7.12 用sub()方法替换字符串正则表达式不仅能找到文本模式，而且能够用新的文本替换掉这些模式。Regex对象的sub()方法需要传入两个参数。第一个参数是一个字符串，用于取代发现的匹配。第二个参数是一个字符串，是用正则表达式匹配的内容。sub()方法返回替换完成后的字符串。

例如，在交互式环境中输入以下代码：>>> namesRegex = re.compile(r'Agent \w+') >>> namesRegex.sub('CENSORED', 'Agent Alice gave the secret documents to Agent Bob.') 'CENSORED gave the secret documents to CENSORED.'

有时候，你可能需要使用匹配的文本本身，作为替换的一部分。在sub()的第一个参数中，可以输入\1、\2、\3……。表示"在替换中输入分组1、2、3……的文本"。

例如，假定想要隐去密探的姓名，只显示他们姓名的第一个字母。要做到这一点，可以使用正则表达式Agent (\w)\w，传入r'\1 *'作为sub()的第一个参数。字符串中的\1将由分组1匹配的文本所替代，也就是正则表达式的(\w)分组。>>> agentNamesRegex = re.compile(r'Agent (\w)\w*') >>> agentNamesRegex.sub(r'\1****', 'Agent Alice told Agent Carol that AgentEve knew Agent Bob was a double agent.') A**** told C**** that E**** knew B**** was a double agent.'

## 7.13 管理复杂的正则表达式如果要匹配的文本模式很简单，正则表达式就很好。但匹配复杂的文本模式，可能需要长的、费解的正则表达式。你可以告诉re.compile()，忽略正则表达式字符串中的空白符和注释，从而缓解这一点。要实现这种详细模式，可以向re.compile()传入变量re.VERBOSE，作为第二个参数。

现在，不必使用这样难以阅读的正则表达式：phoneRegex = re.compile(r'((\d{3}|\(\d{3}\))?(\s|-|\.)?\d{3}(\s|-|\.)\d{4} (\s*(ext|x|ext.)\s*\d{2,5})?)')

你可以将正则表达式放在多行中，并加上注释，像这样：phoneRegex = re.compile(r'''( (\d{3}|\(\d{3}\))? # area code (\s|-|\.)? # separator \d{3} # first 3 digits (\s|-|\.) # separator \d{4} # last 4 digits (\s*(ext|x|ext.)\s*\d{2,5})? # extension )''', re.VERBOSE)

请注意，前面的例子使用了三重引号('")，创建了一个多行字符串。这样就可以将正则表达式定义放在多行中，让它更可读。

正则表达式字符串中的注释规则，与普通的Python代码一样：

#符号和它后面直到行末的内容，都被忽略。而且，表示正则表达式的多行字符串中，多余的空白字符也不认为是要匹配的文本模式的一部分。这让你能够组织正则表达式，让它更可读。

## 7.14 组合使用re.IGNORECASE、re.DOTALL和re.VERBOSE

如果你希望在正则表达式中使用re.VERBOSE来编写注释，还希望使用re.IGNORECASE来忽略大小写，该怎么办？遗憾的是，re.compile()函数只接受一个值作为它的第二参数。可以使用管道字符（|）将变量组合起来，从而绕过这个限制。管道字符在这里称为"按位或"操作符。

所以，如果希望正则表达式不区分大小写，并且句点字符匹配换行，就可以这样构造re.compile()调用：>>> someRegexValue = re.compile('foo', re.IGNORECASE | re.DOTALL)

使用第二个参数的全部3个选项，看起来像这样：>>> someRegexValue = re.compile('foo', re.IGNORECASE | re.DOTALL | re.VERBOSE)

这个语法有一点老式，源自于早期的Python版本。位运算符的细节超出了本书的范围，更多的信息请查看资源http://nostarch.com/automatestuff/ 。可以向第二个参数传入其他选项，它们不常用，但你也可以在前面的资源中找到有关它们的信息。

## 7.15 项目：电话号码和E-mail地址提取程序假设你有一个无聊的任务，要在一篇长的网页或文章中，找出所有电话号码和邮件地址。如果手动翻页，可能需要查找很长时间。如果有一个程序，可以在剪贴板的文本中查找电话号码和E-mail地址，那你就只要按一下Ctrl-A选择所有文本，按下Ctrl-C将它复制到剪贴板，然后运行你的程序。它会用找到的电话号码和E-mail地址，替换掉剪贴板中的文本。

当你开始接手一个新项目时，很容易想要直接开始写代码。但更多的时候，最好是后退一步，考虑更大的图景。我建议先草拟高层次的计划，弄清楚程序需要做什么。暂时不要思考真正的代码，稍后再来考虑。现在，先关注大框架。

例如，你的电话号码和E-mail地址提取程序需要完成以下任务：

- 从剪贴板取得文本。

- 找出文本中所有的电话号码和E-mail地址。

- 将它们粘贴到剪贴板。

现在你可以开始思考，如何用代码来完成工作。代码需要做下面的事情：

- 使用pyperclip模块复制和粘贴字符串。

- 创建两个正则表达式，一个匹配电话号码，另一个匹配E-mail地址。

- 对两个正则表达式，找到所有的匹配，而不只是第一次匹配。

- 将匹配的字符串整理好格式，放在一个字符串中，用于粘贴。

- 如果文本中没有找到匹配，显示某种消息。

这个列表就像项目的路线图。在编写代码时，可以独立地关注其中的每一步。每一步都很好管理。它的表达方式让你知道在Python中如何去做。

### 第1步：为电话号码创建一个正则表达式首先，你需要创建一个正则表达式来查找电话号码。创建一个新文件，输入以下代码，保存为phoneAndEmail.py：

#! python3 # phoneAndEmail.py - Finds phone numbers and email addresses on the clipboard. import pyperclip, re phoneRegex = re.compile(r'''( (\d{3}|\(\d{3}\))? # area code (\s|-|\.)? # separator (\d{3}) # first 3 digits (\s|-|\.) # separator (\d{4}) # last 4 digits (\s*(ext|x|ext\.)\s*(\d{2,5}))? # extension )''', re.VERBOSE) # TODO: Create email regex. # TODO: Find matches in clipboard text. # TODO: Copy results to the clipboard.

TODO注释仅仅是程序的框架。当编写真正的代码时，它们会被替换掉。

电话号码从一个"可选的"区号开始，所以区号分组跟着一个问号。因为区号可能只是3个数字（即\d{3}），或括号中的3个数字（即(\d{3})），所以应该用管道符号连接这两部分。可以对这部分多行字符串加上正则表达式注释# Area code，帮助你记忆(\d{3}|(\d{3}))?要匹配的是什么。

电话号码分割字符可以是空格（\s）、短横（-）或句点（.），所以这些部分也应该用管道连接。这个正则表达式接下来的几部分很简单：3个数字，接下来是另一个分割符，接下来是4个数字。最后的部分是可选的分机号，包括任意数目的空格，接着ext、x或ext.，再接着2到5位数字。

### 第2步：为E-mail地址创建一个正则表达式还需要一个正则表达式来匹配E-mail地址。让你的程序看起来像这样： #! python3 # phoneAndEmail.py - Finds phone numbers and email addresses on the clipboard. import pyperclip, re phoneRegex = re.compile(r'''( --_snip_-- # Create email regex.emailRegex = re.compile(r'''( 1. [a-zA-Z0-9._%+-]+ # username 2. @ # @ symbol 3. [a-zA-Z0-9.-]+ # domain name (\.[a-zA-Z]{2,4}) # dot-something )''', re.VERBOSE) # TODO: Find matches in clipboard text. # TODO: Copy results to the clipboard.

E-mail地址的用户名部分1. 是一个或多个字符，字符可以包括：小写和大写字母、数字、句点、下划线、百分号、加号或短横。可以将所有这些放入一个字符分类：[a-zA-Z0-9._%+-]。

域名和用户名用@符号分割2. ，域名3. 允许的字符分类要少一些，只允许字母、数字、句点和短横：[a-zA-Z0-9.-]。最后是"dot-com"部分（技术上称为"顶级域名"），它实际上可以是"dot-anything"。它有2到4个字符。

E-mail地址的格式有许多奇怪的规则。这个正则表达式不会匹配所有可能的、有效的E-mail地址，但它会匹配你遇到的大多数典型的电子邮件地址。

### 第3步：在剪贴板文本中找到所有匹配既然已经指定了电话号码和电子邮件地址的正则表达式，就可以让 Python的re模块做辛苦的工作，查找剪贴板文本中所有的匹配。pyperclip.paste()函数将取得一个字符串，内容是剪贴板上的文本，findall()正则表达式方法将返回一个元组的列表。

让你的程序看起来像这样： #! python3 # phoneAndEmail.py - Finds phone numbers and email addresses on the clipboard. import pyperclip, re phoneRegex = re.compile(r＇＇＇( --_snip_-- # Find matches in clipboard text.text = str(pyperclip.paste()) 1. matches = [] 2. for groups in phoneRegex.findall(text): phoneNum = '-'.join([groups[1], groups[3], groups[5]]) if groups[8] != '': phoneNum += ' x' + groups[8] matches.append(phoneNum) 3. for groups in emailRegex.findall(text): matches.append(groups[0]) # TODO: Copy results to the clipboard.

每个匹配对应一个元组，每个元组包含正则表达式中每个分组的字符串。回忆一下，分组0匹配整个正则表达式，所以在元组下标0处的分组，就是你感兴趣的内容。

在1. 处可以看到，你将所有的匹配保存在名为matches的列表变量中。它从一个空列表开始，经过几个for循环。对于E-mail地址，你将每次匹配的分组0添加到列表中3. 。对于匹配的电话号码，你不想只是添加分组0。虽然程序可以"检测"几种不同形式的电话号码，你希望添加的电话号码是唯一的、标准的格式。phoneNum变量包含一个字符串，它由匹配文本的分组1、3、5和8构成2. 。（这些分组是区号、前3个数字、后4个数字和分机号。）

### 第4步：所有匹配连接成一个字符串，复制到剪贴板现在，E-mail地址和电话号码已经作为字符串列表放在matches中，你希望将它们复制到剪贴板。pyperclip.copy()函数只接收一个字符串值，而不是字符串的列表，所以你在matches上调用join()方法。

为了更容易看到程序在工作，让我们将所有找到的匹配都输出在终端上。如果没有找到电话号码或E-mail地址，程序应该告诉用户。

让你的程序看起来像这样：

#! python3 # phoneAndEmail.py - Finds phone numbers and email addresses on the clipboard. --_snip_-- for groups in emailRegex.findall(text): matches.append(groups[0]) # Copy results to the clipboard.if len(matches) > 0: pyperclip.copy('\n'.join(matches)) print('Copied to clipboard:') print('\n'.join(matches))else: print('No phone numbers or email addresses found.')

### 第5步：运行程序作为一个例子，打开你的Web浏览器，访问No Starch Press的联系页面http://www.nostarch.com/contactus.htm。按下Ctrl-A选择该页的所有文本，按下Ctrl-C将它复制到剪贴板。运行这个程序，输出看起来像这样：Copied to clipboard: 800-420-7240 415-863-9900 415-863-9950 info@nostarch.com media@nostarch.com academic@nostarch.com help@nostarch.com

### 第6步：类似程序的构想识别文本的模式（并且可能用sub()方法替换它们）有许多不同潜在的应用。

- 寻找网站的URL，它们以http://或https://开始。

- 整理不同日期格式的日期（诸如3/14/2015、03-14-2015和2015/3/14），用唯一的标准格式替代。

- 删除敏感的信息，诸如社会保险号或信用卡号。

- 寻找常见打字错误，诸如单词间的多个空格、不小心重复的单词，或者句子末尾处多个感叹号。它们很烦人！！

## 7.16 小结虽然计算机可以很快地查找文本，但你必须精确地告诉它要找什么。正则表达式让你精确地指明要找的文本模式。实际上，某些文字处理和电子表格应用提供了查找替换功能，让你使用正则表达式进行查找。

Python自带的re模块让你编译Regex对象。该对象有几种方法：search()查找单词匹配，findall()查找所有匹配实例，sub()对文本进行查找和替换。

除本章介绍的语法以外，还有一些正则表达式语法。你可以在官方Python文档中找到更多内容：http://docs.python.org/3/library/re.html 。指南网站http://www.regular- expressions.info/ 也是很有用的资源。

既然已经掌握了如何操纵和匹配字符串，接下来就该学习如何在计算机硬盘上读写文件了。

## 7.17 习题

1．创建Regex对象的函数是什么？

2．在创建Regex对象时，为什么常用原始字符串？

3．search()方法返回什么？

4．通过Match对象，如何得到匹配该模式的实际字符串？

5．用r'(\d\d\d)-(\d\d\d-\d\d\d\d)'创建的正则表达式中，分组0表示什么？分组1呢？分组2呢？

6．括号和句点在正则表达式语法中有特殊的含义。如何指定正则表达式匹配真正的括号和句点字符？

7．findall()方法返回一个字符串的列表，或字符串元组的列表。是什么决定它提供哪种返回？

8．在正则表达式中，|字符表示什么意思？

9．在正则表达式中，?字符有哪两种含义？

10．在正则表达式中，+和*字符之间的区别是什么？

11．在正则表达式中，{3}和{3,5}之间的区别是什么？

12．在正则表达式中，\d、\w和\s缩写字符类是什么意思？

13．在正则表达式中，\D、\W和\S缩写字符类是什么意思？

14．如何让正则表达式不区分大小写？

15．字符.通常匹配什么？如果re.DOTALL作为第二个参数传递给re.compile()，它会匹配什么？

16．.*和.*?之间的区别是什么？

17．匹配所有数字和小写字母的字符分类语法是什么？

18．如果numRegex = re.compile(r'\d+')，那么numRegex.sub('X', '12 drummers, 11 pipers, five rings, 3 hens')返回什么？

19．将re.VERBOSE作为第二个参数传递给re.compile()，让你能做什么？

20．如何写一个正则表达式，匹配每3位就有一个逗号的数字？它必须匹配以下数字：

- '42'- '1,234'- '6,368,745'

但不会匹配：

- '12,34,567' （逗号之间只有两位数字）- '1234' （缺少逗号）

21．如何写一个正则表达式，匹配姓Nakamoto的完整姓名？你可以假定名字总是出现在姓前面，是一个大写字母开头的单词。该正则表达式必须匹配：

- 'Satoshi Nakamoto'- 'Alice Nakamoto'- 'RoboCop Nakamoto'

但不匹配：

- 'satoshi Nakamoto'（名字没有大写首字母）- 'Mr. Nakamoto'（前面的单词包含非字母字符）- 'Nakamoto' （没有名字）- 'Satoshi nakamoto'（姓没有首字母大写）

22．如何编写一个正则表达式匹配一个句子，它的第一个词是Alice、Bob或Carol，第二个词是eats、pets或throws，第三个词是apples、cats或baseballs。该句子以句点结束。这个正则表达式应该不区分大小写。它必须匹配：

- 'Alice eats apples.'- 'Bob pets cats.'- 'Carol throws baseballs.'- 'Alice throws Apples.'- 'BOB EATS CATS.'

但不匹配：

- 'RoboCop eats apples.'- 'ALICE THROWS FOOTBALLS.'- 'Carol eats 7 cats.'

## 7.18 实践项目作为实践，编程完成下列任务。

### 7.18.1 强口令检测写一个函数，它使用正则表达式，确保传入的口令字符串是强口令。强口令的定义是：长度不少于8个字符，同时包含大写和小写字符，至少有一位数字。你可能需要用多个正则表达式来测试该字符串，以保证它的强度。

### 7.18.2 strip()的正则表达式版本写一个函数，它接受一个字符串，做的事情和strip()字符串方法一样。如果只传入了要去除的字符串，没有其他参数，那么就从该字符串首尾去除空白字符。否则，函数第二个参数指定的字符将从该字符串中去除。

[1] Cory Doctorow, "Here's what ICT should really teach kids: how to do regular expressions,"_Guardian_, December 4, 2012, _http://www.theguardian.com/technology/2012/dec/04/ict-teach-kids-regular-expressions/._

# 第10章调试既然你已学习了足够的内容，可以编写更复杂的程序，可能就会在程序中发现不那么简单的缺陷。本章介绍了一些工具和技巧，用于寻找程序中缺陷的根源，帮助你更快更容易地修复缺陷。

程序员之间流传着一个老笑话："编码占了编程工作量的90%，调试占了另外90%。"

计算机只会做你告诉它做的事情，它不会读懂你的心思，做你想要它做的事情。即使专业的程序员也一直在制造缺陷，所以如果你的程序有问题，不必感到沮丧。

好在，有一些工具和技巧可以确定你的代码在做什么，以及哪儿出了问题。首先，你要查看日志和断言。这两项功能可以帮助你尽早发现缺陷。一般来说，缺陷发现的越早，就越容易修复。

其次，你要学习如何使用调试器。调试器是IDLE的一项功能，它可以一次执行一条指令，在代码运行时，让你有机会检查变量的值，并追踪程序运行时值的变化。这比程序全速运行要慢得多，但可以帮助你查看程序运行时其中实际的值，而不是通过源代码推测值可能是什么。

## 10.1 抛出异常当Python试图执行无效代码时，就会抛出异常。在第 3 章中，你已看到如何使用try和except语句来处理Python的异常，这样程序就可以从你预期的异常中恢复。但你也可以在代码中抛出自己的异常。抛出异常相当于是说："停止运行这个函数中的代码，将程序执行转到except语句"。

抛出异常使用raise语句。在代码中，raise语句包含以下部分：

- raise关键字；

- 对Exception函数的调用；

- 传递给Exception函数的字符串，包含有用的出错信息。

例如，在交互式环境中输入以下代码：>>> raise Exception('This is the error message.') Traceback (most recent call last): File "", line 1, in raise Exception('This is the error message.') Exception: This is the error message.

如果没有try和except语句覆盖抛出异常的raise语句，该程序就会崩溃，并显示异常的出错信息。

通常是调用该函数的代码知道如何处理异常，而不是该函数本身。所以你常常会看到raise语句在一个函数中，try和except语句在调用该函数的代码中。例如，打开一个新的文件编辑器窗口，输入以下代码，并保存为boxPrint.py： def boxPrint(symbol, width, height): if len(symbol) != 1: 1. raise Exception('Symbol must be a single character string.') if width <= 2: 2. raise Exception('Width must be greater than 2.') if height <= 2: 3. raise Exception('Height must be greater than 2.') print(symbol * width) for i in range(height - 2): print(symbol + (' ' * (width - 2)) + symbol) print(symbol * width) for sym, w, h in (('*', 4, 4), ('O', 20, 5), ('x', 1, 3), ('ZZ', 3, 3)): try: boxPrint(sym, w, h) 4. except Exception as err: 5. print('An exception happened: ' + str(err))

这里我们定义了一个boxPrint() 函数，它接受一个字符、一个宽度和一个高度。它按照指定的宽度和高度，用该字符创建了一个小盒子的图像。这个盒子被打印到屏幕上。

假定我们希望该字符是一个字符，宽度和高度要大于2。我们添加了if语句，如果这些条件没有满足，就抛出异常。稍后，当我们用不同的参数调用boxPrint()时，try/except语句就会处理无效的参数。

这个程序使用了except语句的except Exception as err形式4. 。如果boxPrint()返回一个Exception对象1. 2. 3. ，这条语句就会将它保存在名为err的变量中。Exception对象可以传递给str()，将它转换为一个字符串，得到用户友好的出错信息5. 。运行boxPrint.py，输出看起来像这样：**** * * * * **** OOOOOOOOOOOOOOOOOOOO O O O O O O OOOOOOOOOOOOOOOOOOOO An exception happened: Width must be greater than 2. An exception happened: Symbol must be a single character string.

使用try和except语句，你可以更优雅地处理错误，而不是让整个程序崩溃。

## 10.2 取得反向跟踪的字符串如果Python遇到错误，它就会生成一些错误信息，称为"反向跟踪"。反向跟踪包含了出错消息、导致该错误的代码行号，以及导致该错误的函数调用的序列。这个序列称为"调用栈"。

在IDLE中打开一个新的文件编辑器窗口，输入以下程序，并保存为error Example.py：def spam(): bacon() def bacon(): raise Exception('This is the error message.') spam()

如果运行errorExample.py，输出看起来像这样：Traceback (most recent call last): File "errorExample.py", line 7, in <module> spam() File "errorExample.py", line 2, in spam bacon() File "errorExample.py", line 5, in bacon raise Exception('This is the error message.') Exception: This is the error message.

通过反向跟踪，可以看到该错误发生在第5行，在bacon() 函数中。这次特定的bacon() 调用来自第2行，在spam() 函数中，它又在第7行被调用的。在从多个位置调用函数的程序中，调用栈就能帮助你确定哪次调用导致了错误。

只要抛出的异常没有被处理，Python 就会显示反向跟踪。但你也可以调用traceback.format_exc()，得到它的字符串形式。如果你希望得到异常的反向跟踪的信息，但也希望except语句优雅地处理该异常，这个函数就很有用。在调用该函数之前，需要导入Python的traceback模块。

例如，不是让程序在异常发生时就崩溃，可以将反向跟踪信息写入一个日志文件，并让程序继续运行。稍后，在准备调试程序时，可以检查该日志文件。在交互式环境中输入以下代码：>>> import traceback >>> try: raise Exception('This is the error message.')except: errorFile = open('errorInfo.txt', 'w') errorFile.write(traceback.format_exc()) errorFile.close() print('The traceback info was written to errorInfo.txt.') 116 The traceback info was written to errorInfo.txt.

write() 方法的返回值是116，因为116个字符被写入到文件中。反向跟踪文本被写入errorInfo.txt。Traceback (most recent call last): File "<pyshell#28>", line 2, in <module> Exception: This is the error message.

## 10.3 断言

"断言"是一个心智正常的检查，确保代码没有做什么明显错误的事情。这些心智正常的检查由assert语句执行。如果检查失败，就会抛出异常。在代码中，assert语句包含以下部分：

- assert关键字；

- 条件（即求值为True或False的表达式）；

- 逗号；

- 当条件为False时显示的字符串。

例如，在交互式环境中输入以下代码：>>> podBayDoorStatus = 'open' >>> assert podBayDoorStatus == 'open', 'The pod bay doors need to be "open".' >>> podBayDoorStatus = 'I\'m sorry, Dave. I\'m afraid I can't do that.'' >>> assert podBayDoorStatus == 'open', 'The pod bay doors need to be "open".' Traceback (most recent call last): File "< pyshell#10>", line 1, in < module> assert podBayDoorStatus == 'open', 'The pod bay doors need to be "open".' AssertionError: The pod bay doors need to be "open".

这里将podBayDoorStatus设置为 'open'，所以从此以后，我们充分期望这个变量的值是 'open'。在使用这个变量的程序中，基于这个值是 'open' 的假定，我们可能写下了大量的代码，即这些代码依赖于它是 'open'，才能按照期望工作。所以添加了一个断言，确保假定podBayDoorStatus是 'open' 是对的。这里，我们加入了信息 'The pod bay doors need to be "open".'，这样如果断言失败，就很容易看到哪里出了错。

稍后，假如我们犯了一个明显的错误，把另外的值赋给podBayDoorStatus，但在很多行代码中，我们并没有意识到这一点。这个断言会抓住这个错误，清楚地告诉我们出了什么错。

在日常英语中，assert语句是说："我断言这个条件为真，如果不为真，程序中什么地方就有一个缺陷。"不像异常，代码不应该用try和except处理assert语句。如果assert失败，程序就应该崩溃。通过这样的快速失败，产生缺陷和你第一次注意到该缺陷之间的时间就缩短了。这将减少为了寻找导致该缺陷的代码，而需要检查的代码量。

断言针对的是程序员的错误，而不是用户的错误。对于那些可以恢复的错误（诸如文件没有找到，或用户输入了无效的数据），请抛出异常，而不是用assert语句检测它。

### 10.3.1 在交通灯模拟中使用断言假定你在编写一个交通信号灯的模拟程序。代表路口信号灯的数据结构是一个字典，以 'ns' 和 'ew' 为键，分别表示南北向和东西向的信号灯。这些键的值可以是 'green'、'yellow' 或 'red' 之一。代码看起来可能像这样：market_2nd = {'ns': 'green', 'ew': 'red'} mission_16th = {'ns': 'red', 'ew': 'green'}

这两个变量将针对Market街和第2街路口，以及Mission街和第16街路口。作为项目启动，你希望编写一个switchLights() 函数，它接受一个路口字典作为参数，并切换红绿灯。

开始你可能认为，switchLights() 只要将每一种灯按顺序切换到下一种顔色：'green' 值应该切换到 'yellow'，'yellow' 应该切换到 'red'，'red' 应该切换到'green'。实现这个思想的代码看起来像这样：def switchLights(stoplight): for key in stoplight.keys(): if stoplight[key] == 'green': stoplight[key] = 'yellow' elif stoplight[key] == 'yellow': stoplight[key] = 'red' elif stoplight[key] == 'red': stoplight[key] = 'green' switchLights(market_2nd)

你可能已经发现了这段代码的问题，但假设你编写了剩下的模拟代码，有几千行，但没有注意到这个问题。当最后运行时，程序没有崩溃，但虚拟的汽车撞车了！

因为你已经编写了剩下的程序，所以不知道缺陷在哪里。也许在模拟汽车的代码中，或者在模拟司机的代码中。可能需要花几个小时追踪缺陷，才能找到switchLights() 函数。

但如果在编写switchLights() 时，你添加了断言，确保至少一个交通灯是红色，可能在函数的底部添加这样的代码：assert 'red' in stoplight.values(), 'Neither light is red! ' + str(stoplight)

有了这个断言，程序就会崩溃，并提供这样的出错信息： Traceback (most recent call last): File "carSim.py", line 14, in <module> switchLights(market_2nd) File "carSim.py", line 13, in switchLights assert 'red' in stoplight.values(), 'Neither light is red! ' + str(stoplight) 1. AssertionError: Neither light is red! {'ns': 'yellow', 'ew': 'green'}

这里重要的一行是AssertionError1. 。虽然程序崩溃并非如你所愿，但它马上指出了心智正常检查失败：两个方向都没有红灯，这意味着两个方向的车都可以走。在程序执行中尽早快速失败，可以省去将来大量的调试工作。

### 10.3.2 禁用断言在运行Python时传入-O选项，可以禁用断言。如果你已完成了程序的编写和测试，不希望执行心智正常检测，从而减慢程序的速度，这样就很好（尽管大多数断言语句所花的时间，不会让你觉察到速度的差异）。断言是针对开发的，不是针对最终产品。当你将程序交给其他人运行时，它应该没有缺陷，不需要进行心智正常检查。如何用-O选项启动也许并不疯狂的程序，详细内容请参考附录B。

## 10.4 日志如果你曾经在代码中加入print() 语句，在程序运行时输出某些变量的值，你就使用了记日志的方式来调试代码。记日志是一种很好的方式，可以理解程序中发生的事，以及事情发生的顺序。Python的logging模块使得你很容易创建自定义的消息记录。这些日志消息将描述程序执行何时到达日志函数调用，并列出你指定的任何变量当时的值。另一方面，缺失日志信息表明有一部分代码被跳过，从未执行。

### 10.4.1 使用日志模块要启用logging模块，在程序运行时将日志信息显示在屏幕上，请将下面的代码复制到程序顶部（但在Python的#!行之下）：import logging logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')

你不需要过于担心它的工作原理，但基本上，当 Python 记录一个事件的日志时，它会创建一个LogRecord对象，保存关于该事件的信息。logging模块的函数让你指定想看到的这个LogRecord对象的细节，以及希望的细节展示方式。

假如你编写了一个函数，计算一个数的阶乘。在数学上，4 的阶乘是1 × 2 × 3 × 4，即24。7的阶乘是1 × 2 × 3 × 4 × 5 × 6 × 7，即5040。打开一个新的文件编辑器窗口，输入以下代码。其中有一个缺陷，但你也会输入一些日志信息，帮助你弄清楚哪里出了问题。将该程序保存为factorialLog.py。import logging logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s') logging.debug('Start of program') def factorial(n): logging.debug('Start of factorial(%s%%)' % (n)) total = 1 for i in range(n + 1): total *= i logging.debug('i is ' + str(i) + ', total is ' + str(total)) logging.debug('End of factorial(%s%%)' % (n)) return total print(factorial(5)) logging.debug('End of program')

这里，我们在想打印日志信息时，使用logging.debug() 函数。这个debug() 函数将调用basicConfig()，打印一行信息。这行信息的格式是我们在 basicConfig()函数中指定的，并且包括我们传递给 debug() 的消息。print（factorial（5））调用是原来程序的一部分，所以就算禁用日志信息，结果仍会显示。

这个程序的输出就像这样：2015-05-23 16:20:12,664 - DEBUG - Start of program 2015-05-23 16:20:12,664 - DEBUG - Start of factorial(5) 2015-05-23 16:20:12,665 - DEBUG - i is 0, total is 0 2015-05-23 16:20:12,668 - DEBUG - i is 1, total is 0 2015-05-23 16:20:12,670 - DEBUG - i is 2, total is 0 2015-05-23 16:20:12,673 - DEBUG - i is 3, total is 0 2015-05-23 16:20:12,675 - DEBUG - i is 4, total is 0 2015-05-23 16:20:12,678 - DEBUG - i is 5, total is 0 2015-05-23 16:20:12,680 - DEBUG - End of factorial(5) 0 2015-05-23 16:20:12,684 - DEBUG - End of program

factorial() 函数返回0作为5的阶乘，这是不对的。for循环应该用从1到5的数，乘以total的值。但logging.debug() 显示的日志信息表明，i变量从0开始，而不是1。因为0乘任何数都是0，所以接下来的迭代中，total的值都是错的。日志消息提供了可以追踪的痕迹，帮助你弄清楚何时事情开始不对。

将代码行for i in range（n + 1）：改为for i in range（1，n + 1）：，再次运行程序。输出看起来像这样：2015-05-23 17:13:40,650 - DEBUG - Start of program 2015-05-23 17:13:40,651 - DEBUG - Start of factorial(5) 2015-05-23 17:13:40,651 - DEBUG - i is 1, total is 1 2015-05-23 17:13:40,654 - DEBUG - i is 2, total is 2 2015-05-23 17:13:40,656 - DEBUG - i is 3, total is 6 2015-05-23 17:13:40,659 - DEBUG - i is 4, total is 24 2015-05-23 17:13:40,661 - DEBUG - i is 5, total is 120 2015-05-23 17:13:40,661 - DEBUG - End of factorial(5) 120 2015-05-23 17:13:40,666 - DEBUG - End of program

factorial（5）调用正确地返回120。日志消息表明循环内发生了什么，这直接指向了缺陷。

你可以看到，logging.debug() 调用不仅打印出了传递给它的字符串，而且包含一个时间戳和单词DEBUG。

### 10.4.2 不要用print()调试输入import logging和logging.basicConfig（level=logging.DEBUG, format='% (asctime)s - %(levelname)s - %(message)s'）有一点不方便。你可能想使用print() 调用代替，但不要屈服于这种诱惑！在调试完成后，你需要花很多时间，从代码中清除每条日志消息的print() 调用。你甚至有可能不小心删除一些print() 调用，而它们不是用来产生日志消息的。日志消息的好处在于，你可以随心所欲地在程序中想加多少就加多少，稍后只要加入一次logging.disable（logging.CRITICAL）调用，就可以禁止日志。不像print()，logging模块使得显示和隐藏日志信息之间的切换变得很容易。

日志消息是给程序员的，不是给用户的。用户不会因为你便于调试，而想看到的字典值的内容。请将日志信息用于类似这样的目的。对于用户希望看到的消息，例如"文件未找到"或者"无效的输入，请输入一个数字"，应该使用print() 调用。我们不希望禁用日志消息之后，让用户看不到有用的信息。

### 10.4.3 日志级别

"日志级别"提供了一种方式，按重要性对日志消息进行分类。5个日志级别如表10-1所示，从最不重要到最重要。利用不同的日志函数，消息可以按某个级别记入日志。

表10-1 Python中的日志级别级别日志函数描述

DEBUG

logging.debug()

最低级别。用于小细节。通常只有在诊断问题时，你才会关心这些消息

INFO

logging.info()

用于记录程序中一般事件的信息，或确认一切工作正常

WARNING

logging.warning()

用于表示可能的问题，它不会阻止程序的工作，但将来可能会

ERROR

logging.error()

用于记录错误，它导致程序做某事失败

CRITICAL

logging.critical()

最高级别。用于表示致命的错误，它导致或将要导致程序完全停止工作日志消息作为一个字符串，传递给这些函数。日志级别是一种建议。归根到底，还是由你来决定日志消息属于哪一种类型。在交互式环境中输入以下代码：>>> import logging >>> logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s -%(levelname)s - %(message)s') >>> logging.debug('Some debugging details.') 2015-05-18 19:04:26,901 - DEBUG - Some debugging details. >>> logging.info('The logging module is working.') 2015-05-18 19:04:35,569 - INFO - The logging module is working. >>> logging.warning('An error message is about to be logged.') 2015-05-18 19:04:56,843 - WARNING - An error message is about to be logged. >>> logging.error('An error has occurred.') 2015-05-18 19:05:07,737 - ERROR - An error has occurred. >>> logging.critical('The program is unable to recover!') 2015-05-18 19:05:45,794 - CRITICAL - The program is unable to recover!

日志级别的好处在于，你可以改变想看到的日志消息的优先级。向basicConfig()函数传入logging.DEBUG作为level关键字参数，这将显示所有日志级别的消息（DEBUG是最低的级别）。但在开发了更多的程序后，你可能只对错误感兴趣。在这种情况下，可以将basicConfig() 的level参数设置为logging.ERROR，这将只显示ERROR和CRITICAL消息，跳过DEBUG、INFO和WARNING消息。

### 10.4.4 禁用日志在调试完程序后，你可能不希望所有这些日志消息出现在屏幕上。logging. disable() 函数禁用了这些消息，这样就不必进入到程序中，手工删除所有的日志调用。只要向logging.disable() 传入一个日志级别，它就会禁止该级别和更低级别的所有日志消息。所以，如果想要禁用所有日志，只要在程序中添加logging. disable（logging.CRITICAL）。例如，在交互式环境中输入以下代码：>>> import logging >>> logging.basicConfig(level=logging.INFO, format=' %(asctime)s -%(levelname)s - %(message)s') >>> logging.critical('Critical error! Critical error!') 2015-05-22 11:10:48,054 - CRITICAL - Critical error! Critical error! >>> logging.disable(logging.CRITICAL) >>> logging.critical('Critical error! Critical error!') >>> logging.error('Error! Error!')

因为logging.disable() 将禁用它之后的所有消息，你可能希望将它添加到程序中接近import logging代码行的位置。这样就很容易找到它，根据需要注释掉它，或取消注释，从而启用或禁用日志消息。

### 10.4.5 将日志记录到文件除了将日志消息显示在屏幕上，还可以将它们写入文本文件。logging.basic Config() 函数接受filename关键字参数，像这样：import logging logging.basicConfig(filename='myProgramLog.txt' , level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')

日志信息将被保存到myProgramLog.txt文件中。虽然日志消息很有用，但它们可能塞满屏幕，让你很难读到程序的输出。将日志信息写入到文件，让屏幕保持干净，又能保存信息，这样在运行程序后，可以阅读这些信息。可以用任何文件编辑器打开这个文本文件，诸如Notepad或TextEdit。

## 10.5 IDLE的调试器

"调试器"是IDLE的一项功能，让你每次执行一行程序。调试器将运行一行代码，然后等待你告诉它继续。像这样让程序运行"在调试器之下"，你可以随便花多少时间，检查程序运行时任意一个时刻的变量的值。对于追踪缺陷，这是一个很有价值的工具。

要启用IDLE的调试器，就在交互式环境窗口中点击DebugDebugger。这将打开调试控制（Debug Control）窗口，如图10-1所示。

图10-1 调试控制窗口当调试控制窗口出现后，勾选全部4个复选框：Stack、Locals、Source和Globals。这样窗口将显示全部的调试信息。调试控制窗口显示时，只要你从文件编辑器运行程序，调试器就会在第一条指令之前暂停执行，并显示下面的信息：

- 将要执行的代码行；

- 所有局部变量及其值的列表；

- 所有全局变量及其值的列表。

你会注意到，在全局变量列表中，有一些变量你没有定义，诸如 builtins 、 doc 、 file ，等等。它们是Python在运行程序时，自动设置的变量。这些变量的含义超出了本书的范围，你可以暂时忽略它们。

程序将保持暂停，直到你按下调试控制窗口的5个按钮中的一个：Go、Step、Over、Out或Quit。

### 10.5.1 Go

点击Go按钮将导致程序正常执行至终止，或到达一个"断点"（断点在本章稍后介绍）。如果你完成了调试，希望程序正常继续，就点击Go按钮。

### 10.5.2 Step

点击Step按钮将导致调试器执行下一行代码，然后再次暂停。如果变量的值发生了变化，调试控制窗口的全局变量和局部变量列表就会更新。如果下一行代码是一个函数调用，调试器就会"步入"那个函数，跳到该函数的第一行代码。

### 10.5.3 Over

点击Over按扭将执行下一行代码，与Step按钮类似。但是，如果下一行代码是函数调用，Over按钮将"跨过"该函数的代码。该函数的代码将以全速执行，调试器将在该函数返回后暂停。例如，如果下一行代码是print() 调用，你实际上不关心内建print() 函数中的代码，只希望传递给它的字符串打印在屏幕上。出于这个原因，使用Over按钮比使用Step按钮更常见。

### 10.5.4 Out

点击Out按钮将导致调试器全速执行代码行，直到它从当前函数返回。如果你用Step按钮进入了一个函数，现在只想继续执行指令，直到该函数返回，那就点击Out按钮，从当前的函数调用"走出来"。

### 10.5.5 Quit

如果你希望完全停止调试，不必继续执行剩下的程序，就点击Quit按钮。Quite按钮将马上终止该程序。如果你希望再次正常运行你的程序，就再次选择DebugDebugger，禁用调试器。

### 10.5.6 调试一个数字相加的程序打开一个新的文件编辑器窗口，输入以下代码：print('Enter the first number to add:') first = input() print('Enter the second number to add:') second = input() print('Enter the third number to add:') third = input() print('The sum is ' + first + second + third)

将它保存为buggyAddingProgram.py，不启用调试器，第一次运行它。程序的输出像这样：Enter the first number to add: 5 Enter the second number to add: 3 Enter the third number to add: 42 The sum is 5342

这个程序没有崩溃，但求和显然是错的。让我们启用调试控制窗口，再次运行它，这次在调试器控制之下。

当你按下F5或选择RunRun Module（启用DebugDebugger，选中调试控制窗口的所有4个复选框），程序启动时将暂停在第1行。调试器总是会暂停在它将要执行的代码行上。调试控制窗口看起来如图10-2所示。

图10-2 程序第一次在调试器下运行时的调试控制窗口点击一次Over按钮，执行第一个print() 调用。这里应该使用Over按钮，而不是Step，因为你不希望进入到print() 函数的代码中。调试控制窗口将更新到第2行，文件编辑器窗口的第2行将高亮显示，如图10-3所示。这告诉你程序当前执行到哪里。

图10-3 点击Over按钮后的调试控制窗口再次点击Over按钮，执行input() 函数调用，当IDLE等待你在交互式环境窗口中为input() 调用输入内容时，调试控制窗口中的按钮将被禁用。输入5并按回车。调试控制窗口按钮将重新启用。

继续点击Over按钮，输入3和42作为接下来的两个数，直到调试器位于第7行，程序中最后的print() 调用。调试控制窗口应该如图10-4所示。可以看到，在全局变量的部分，第一个、第二个和第三个变量设置为字符串值，而不是整型值。当最后一行执行时，这些字符串连接起来，而不是加起来，导致了这个缺陷。

用调试器单步执行程序很有用，但也可能很慢。你常常希望程序正常运行，直到它到达特定的代码行。你可以使用断点，让调试器做到这一点。

### 10.5.7 断点

"断点"可以设置在特定的代码行上，当程序执行到达该行时，它迫使调试器暂停。在一个新的文件编辑器窗口中，输入以下程序，它模拟投掷1000次硬币。将它保存为coinFlip.py。

图10-4 在最后一行的调试控制窗口。这些变量被设置为字符串，导致了这个缺陷 import random heads = 0 for i in range(1, 1001): 1. if random.randint(0, 1) == 1: heads = heads + 1 if i == 500: 2. print('Halfway done!') print('Heads came up ' + str(heads) + ' times.')

在半数时间里，random.randint（0，1）调用1. 将返回0，在另外半数时间将返回1。这可以用来模拟50/50的硬币投掷，其中1代表正面。当不用调试器运行该程序时，它很快输出下面的内容：Halfway done! Heads came up 490 times.

如果启用调试器运行这个程序，就必须点击几千次Over按钮，程序才能结束。如果你对程序执行到一半时heads的值感兴趣，等1000次硬币投掷完500次，可以在代码行print（'Halfway done!'）2. 上设置断点。要设置断点，在文件编辑器中该行代码上点击右键，并选择Set Breakpoint，如图10-5所示。

图10-5 设置断点你不会在if语句上设置断点，因为if语句会在循环的每次迭代中都执行。通过在if语句内的代码上设置断点，调试器就会只在执行进入if语句时才中断。

带有断点的代码行会在文件编辑器中以黄色高亮显示。如果在调试器下运行该程序，开始它会暂停在第一行，像平时一样。但如果点击Go，程序将全速运行，直到设置了断点的代码行。然后可以点击Go、Over、Step或Out，正常继续。

如果希望清除断点，在文件编辑器中该行代码上点击右键，并从菜单中选择Clear Breakpoint。黄色高亮消失，以后调试器将不会在该行代码上中断。

## 10.6 小结断言、异常、日志和调试器，都是在程序中发现和预防缺陷的有用工具。用Python语句实现的断言，是实现心智正常检查的好方式。如果必要的条件没有保持为True，它将尽早给出警告。断言所针对的错误，是程序不应该尝试恢复的，而是应该快速失败。否则，你应该抛出异常。

异常可以由try和except语句捕捉和处理。logging模块是一种很好的方式，可以在运行时查看代码的内部，它比使用print() 函数要方便得多，因为它有不同的日志级别，并能将日志写入文本文件。

调试器让你每次单步执行一行代码。或者，可以用正常速度运行程序，并让调试器暂停在设置了断点的代码行上。利用调试器，你可以看到程序在运行期间，任何时候所有变量的值。

这些调试工具和技术将帮助你编写正确工作的程序。不小心在代码中引入缺陷，这是不可避免的，不论你有多少年的编码经验。

## 10.7 习题

1．写一条 assert 语句，如果变量 spam 是一个小于 10 的整数，就触发AssertionError。

2．编写一条assert语句，如果eggs和bacon包含的字符串彼此相同，而且不论大小写如何，就触发AssertionError（也就是说，'hello' 和 'hello' 被认为相同，'goodbye' 和 'GOODbye' 也被认为相同）。

3．编写一条assert语句，总是触发AssertionError。

4．为了能调用logging.debug()，程序中必须加入哪两行代码？

5．为了让logging.debug() 将日志消息发送到名为programLog.txt的文件中，程序必须加入哪两行代码？

6．5个日志级别是什么？

7．你可以加入哪一行代码，禁用程序中所有的日志消息？

8．显示同样的消息，为什么使用日志消息比使用print() 要好？

9．调试控制窗口中的Step、Over和Out按钮有什么区别？

10．在点击调试控制窗口中的Go按钮后，调试器何时会停下来？

11．什么是断点？

12．在IDLE中，如何在一行代码上设置断点？

## 10.8 实践项目作为实践，编程完成下面的任务。

### 调试硬币抛掷下面程序的意图是一个简单的硬币抛掷猜测游戏。玩家有两次猜测机会（这是一个简单的游戏）。但是，程序中有一些缺陷。让程序运行几次，找出缺陷，使该程序能正确运行。import random guess = '' while guess not in ('heads', 'tails'): print('Guess the coin toss! Enter heads or tails:') guess = input() toss = random.randint(0, 1) # 0 is tails, 1 is heads if toss == guess: print('You got it!') else: print('Nope! Guess again!') guesss = input() if toss == guess: print('You got it!') else: print('Nope. You are really bad at this game.')

# 第16章发送电子邮件和短信检查和答复电子邮件会占用大量的时间。当然，你不能只写一个程序来处理所有电子邮件，因为每个消息都需要有自己的回应。但是，一旦知道怎么编写收发电子邮件的程序，就可以自动化大量与电子邮件相关的任务。

例如，也许你有一个电子表格，包含许多客户记录，希望根据他们的年龄和位置信息，向每个客户发送不同格式的邮件。商业软件可能无法做这一点。好在，可以编写自己的程序来发送这些电子邮件，节省了大量复制和粘贴电子邮件的时间。

也可以编程发送电子邮件和短信，即使你远离计算机时，也能通知你。如果要自动化的任务需要执行几个小时，你不希望每过几分钟就回到计算机旁边，检查程序的状态。相反，程序可以在完成时向手机发短信，让你在离开计算机时，能专注于更重要的事情。

## 16.1 SMTP

正如HTTP是计算机用来通过因特网发送网页的协议，简单邮件传输协议（SMTP）是用于发送电子邮件的协议。SMTP 规定电子邮件应该如何格式化、加密、在邮件服务器之间传递，以及在你点击发送后，计算机要处理的所有其他细节。但是，你并不需要知道这些技术细节，因为Python的smtplib模块将它们简化成几个函数。

SMTP只负责向别人发送电子邮件。另一个协议，名为IMAP，负责取回发送给你的电子邮件，在16.3节"IMAP"中介绍。

## 16.2 发送电子邮件你可能对发送电子邮件很熟悉，通过Outlook、Thunderbird或某个网站，如Gmail或雅虎邮箱。遗憾的是，Python没有像这些服务一样提供一个漂亮的图形用户界面。作为替代，你调用函数来执行SMTP的每个重要步骤，就像下面的交互式环境的例子。

注意不要在IDLE中输入这个例子，因为smtp.example.com、bob@example.com、MY_ SECRET_PASSWORD和alice@example.com只是占位符。这段代码仅仅勾勒出Python发送电子邮件的过程。>>> import smtplib >>> smtpObj = smtplib.SMTP('smtp.example.com', 587) >>> smtpObj.ehlo() (250, b'mx.example.com at your service, [216.172.148.131]\nSIZE 35882577\ n8BITMIME\nSTARTTLS\nENHANCEDSTATUSCODES\nCHUNKING') >>> smtpObj.starttls() (220, b'2.0.0 Ready to start TLS') >>> smtpObj.login('bob@example.com', 'MY_SECRET_PASSWORD ') (235, b'2.7.0 Accepted') >>> smtpObj.sendmail('bob@example.com', 'alice@example.com', 'Subject: Solong.\nDear Alice, so long and thanks for all the fish. Sincerely, Bob') {} >>> smtpObj.quit() (221, b'2.0.0 closing connection ko10sm23097611pbd.52 - gsmtp')

在下面的小节中，我们将探讨每一步，用你的信息替换占位符，连接并登录到SMTP服务器，发送电子邮件，并从服务器断开连接。

### 16.2.1 连接到SMTP服务器如果你曾设置了Thunderbird、Outlook或其他程序，连接到你的电子邮件账户，你可能熟悉配置SMTP服务器和端口。这些设置因电子邮件提供商而不同，但在网上搜索"< 你的提供商> SMTP设置"，应该能找到相应的服务器和端口。

SMTP服务器的域名通常是电子邮件提供商的域名，前面加上SMTP。例如，Gmail的 SMTP 服务器是smtp.gmail.com。表 16-1 列出了一些常见的电子邮件提供商及其SMTP服务器（端口是一个整数值，几乎总是587，该端口由命令加密标准TLS使用）。

表16-1 电子邮件提供商及其SMTP服务器提供商

SMTP服务器域名

Gmail

smtp.gmail.com

Outlook.com/Hotmail.com

smtp-mail.outlook.com

Yahoo Mail

smtp.mail.yahoo.com

AT&T

smpt.mail.att.net (port 465)

Comcast

smtp.comcast.net

Verizon

smtp.verizon.net (port 465)

得到电子邮件提供商的域名和端口信息后，调用smtplib.SMTP()创建一个SMTP对象，传入域名作为一个字符串参数，传入端口作为整数参数。SMTP对象表示与SMTP邮件服务器的连接，它有一些发送电子邮件的方法。例如，下面的调用创建了一个SMTP对象，连接到Gmail：>>> smtpObj = smtplib.SMTP('smtp.gmail.com', 587) >>> type(smtpObj) < class 'smtplib.SMTP'>

输入type(smtpObj)表明，smtpObj中保存了一个SMTP对象。你需要这个SMTP对象，以便调用它的方法，登录并发送电子邮件。如果smtplib.SMTP()调用不成功，你的SMTP服务器可能不支持TLS端口587。在这种情况下，你需要利用smtplib.SMTP_SSL()和465端口，来创建SMTP对象。>>> smtpObj = smtplib.SMTP_SSL('smtp.gmail.com', 465)

注意如果没有连接到因特网，Python将抛出socket.gaierror: [Errno 11004] getaddrinfo failed或类似的异常。

对于你的程序，TLS和SSL之间的区别并不重要。只需要知道你的SMTP服务器使用哪种加密标准，这样就知道如何连接它。在接下来的所有交互式环境示例中，smtpObj变量将包含smtplib.SMTP()或smtplib.SMTP_SSL()函数返回的SMTP对象。

### 16.2.2 发送SMTP的"Hello"消息得到SMTP对象后，调用它的名字古怪的EHLO()方法，向SMTP电子邮件服务器"打招呼"。这种问候是SMTP中的第一步，对于建立到服务器的连接是很重要的。你不需要知道这些协议的细节。只要确保得到SMTP对象后，第一件事就是调用ehlo()方法，否则以后的方法调用会导致错误。下面是一个ehlo()调用和返回值的例子：>>> smtpObj.ehlo() (250, b'mx.google.com at your service, [216.172.148.131]\nSIZE 35882577\ n8BITMIME\nSTARTTLS\nENHANCEDSTATUSCODES\nCHUNKING')

如果在返回的元组中，第一项是整数250（SMTP中"成功"的代码），则问候成功了。

### 16.2.3 开始TLS加密如果要连接到SMTP服务器的587端口（即使用TLS加密），接下来需要调用starttls()方法。这是为连接实现加密必须的步骤。如果要连接到465端口（使用SSL），加密已经设置好了，你应该跳过这一步。

下面是starttls()方法调用的例子：>>> smtpObj.starttls() (220, b'2.0.0 Ready to start TLS')

starttls()让SMTP连接处于TLS模式。返回值220告诉你，该服务器已准备就绪。

### 16.2.4 登录到SMTP服务器到SMTP服务器的加密连接建立后，可以调用login()方法，用你的用户名（通常是你的电子邮件地址）和电子邮件密码登录。>>> smtpObj.login('my_email_address@gmail.com ', 'MY_SECRET_PASSWORD ') (235, b'2.7.0 Accepted')

传入电子邮件地址字符串作为第一个参数，密码字符串作为第二个参数。返回值235表示认证成功。如果密码不正确，Python会抛出smtplib. SMTPAuthenticationError异常。

将密码放在源代码中要当心。如果有人复制了你的程序，他们就能访问你的电子邮件账户！调用input()，让用户输入密码是一个好主意。每次运行程序时输入密码可能不方便，但这种方法不会在未加密的文件中留下你的密码，黑客或笔记本电脑窃贼不会轻易地得到它。

### 16.2.5 发送电子邮件登录到电子邮件提供商的SMTP服务器后，可以调用的sendmail()方法来发送电子邮件。sendmail()方法调用看起来像这样：>>> smtpObj.sendmail('my_email_address@gmail.com ', 'recipient@example.com ','Subject: So long.\nDear Alice, so long and thanks for all the fish. Sincerely,Bob') {}

sendmail()方法需要三个参数。

- 你的电子邮件地址字符串（电子邮件的"from"地址）。

- 收件人的电子邮件地址字符串，或多个收件人的字符串列表（作为"to"地址）。

- 电子邮件正文字符串。

电子邮件正文字符串必须以'Subject: \n'开头，作为电子邮件的主题行。'\n'换行符将主题行与电子邮件的正文分开。

sendmail()的返回值是一个字典。对于电子邮件传送失败的每个收件人，该字典中会有一个键值对。空的字典意味着对所有收件人已成功发送电子邮件。

Gmail应用程序专用密码

Gmail有针对谷歌账户的附加安全功能，称为应用程序专用密码。如果当你的程序试图登录时，收到"需要应用程序专用密码"的错误信息，就必须在Python脚本设置这样一个密码。具体如何设置谷歌账户的应用程序专用密码，参见http://nostarch.com/automatestuff/ 。

### 16.2.6 从SMTP服务器断开确保在完成发送电子邮件时，调用quit()方法。这让程序从SMTP服务器断开。>>> smtpObj.quit() (221, b'2.0.0 closing connection ko10sm23097611pbd.52 - gsmtp')

返回值221表示会话结束。

要复习连接和登录服务器、发送电子邮件和断开的所有步骤，请参阅 16.2节"发送电子邮件"。

## 16.3 IMAP

正如SMTP是用于发送电子邮件的协议，因特网消息访问协议（IMAP）规定了如何与电子邮件服务提供商的服务器通信，取回发送到你的电子邮件地址的电子邮件。Python带有一个imaplib模块，但实际上第三方的imapclient模块更易用。本章介绍了如何使用IMAPClient，完整的文档在http://imapclient.readthedocs.org/ 。

imapclient模块从IMAP服务器下载电子邮件，格式相当复杂。你很可能希望将它们从这种格式转换成简单的字符串。pyzmail模块替你完成解析这些邮件的辛苦工作。在http://www.magiksys.net/pyzmail/ 可以找到PyzMail的完整文档。

从终端窗口安装imapclient和pyzmail。附录A包含了如何安装第三方模块的步骤。

## 16.4 用IMAP获取和删除电子邮件在Python中，查找和获取电子邮件是一个多步骤的过程，需要第三方模块imapclient和pyzmail。作为概述，这里有一个完整的例子，包括登录到IMAP服务器，搜索电子邮件，获取它们，然后从中提取电子邮件的文本。>>> import imapclient >>> imapObj = imapclient.IMAPClient('imap.gmail.com', ssl=True) >>> imapObj.login('my_email_address@gmail.com ', 'MY_SECRET_PASSWORD ') 'my_email_address@gmail.com Jane Doe authenticated (Success)' >>> imapObj.select_folder('INBOX', readonly=True) >>> UIDs = imapObj.search(['SINCE 05-Jul-2014']) >>> UIDs [40032, 40033, 40034, 40035, 40036, 40037, 40038, 40039, 40040, 40041] >>> rawMessages = imapObj.fetch([40041], ['BODY[]', 'FLAGS']) >>> import pyzmail >>> message = pyzmail.PyzMessage.factory(rawMessages[40041]['BODY[]']) >>> message.get_subject() 'Hello!' >>> message.get_addresses('from') [('Edward Snowden', 'esnowden@nsa.gov')] >>> message.get_addresses('to') [(Jane Doe', 'jdoe@example.com')] >>> message.get_addresses('cc') [] >>> message.get_addresses('bcc') [] >>> message.text_part != None True >>> message.text_part.get_payload().decode(message.text_part.charset) 'Follow the money.\r\n\r\n-Ed\r\n' >>> message.html_part != None True >>> message.html_part.get_payload().decode(message.html_part.charset) '< div dir="ltr">< div>So long, and thanks for all the fish!< br>< br>< /div>- Al< br>< /div>\r\n' >>> imapObj.logout()

你不必记住这些步骤。在详细介绍每一步之后，你可以回来看这个概述，加强记忆。

### 16.4.1 连接到IMAP服务器就像你需要一个SMTP对象连接到SMTP服务器并发送电子邮件一样，你需要一个IMAPClient对象，连接到IMAP服务器并接收电子邮件。首先，你需要电子邮件服务提供商的IMAP服务器域名。这和SMTP服务器的域名不同。表16-2列出了几个流行的电子邮件服务提供商的IMAP服务器。

表16-2 电子邮件提供商及其IMAP服务器提供商

IMAP服务器域名

Gmail

imap.gmail.com

Outlook.com/Hotmail.com

imap-mail.outlook.com

Yahoo Mail

imap.mail.yahoo.com

AT&T

imap.mail.att.net

Comcast

imap.comcast.net

Verizon

incoming.verizon.net

得到IMAP服务器域名后，调用imapclient.IMAPClient()函数，创建一个IMAPClient对象。大多数电子邮件提供商要求SSL加密，传入SSL= TRUE关键字参数。在交互式环境中输入以下代码（使用你的提供商的域名）：>>> import imapclient >>> imapObj = imapclient.IMAPClient('imap.gmail.com', ssl=True)

在接下来的小节里所有交互式环境的例子中，imapObj变量将包含imapclient.IMAPClient()函数返回的IMAPClient对象。在这里，客户端是连接到服务器的对象。

### 16.4.2 登录到IMAP服务器取得IMAPClient对象后，调用它的login()方法，传入用户名（这通常是你的电子邮件地址）和密码字符串。>>> imapObj.login('my_email_address@gmail.com ', 'MY_SECRET_PASSWORD ') 'my_email_address@gmail.com Jane Doe authenticated (Success)'

要记住，永远不要直接在代码中写入密码！应该让程序从input()接受输入的密码。

如果IMAP服务器拒绝用户名/密码的组合，Python会抛出imaplib.error异常。对于Gmail账户，你可能需要使用应用程序专用的密码。详细信息请参阅16.2.5节中的"Gmail应用程序专用密码"。

### 16.4.3 搜索电子邮件登录后，实际获取你感兴趣的电子邮件分为两步。首先，必须选择要搜索的文件夹。然后，必须调用IMAPClient对象的search()方法，传入IMAP搜索关键词字符串。

### 16.4.4 选择文件夹几乎每个账户默认都有一个INBOX文件夹，但也可以调用IMAPClient对象的list_folders()方法，获取文件夹列表。这将返回一个元组的列表。每个元组包含一个文件夹的信息。输入以下代码，继续交互式环境的例子：>>> import pprint >>> pprint.pprint(imapObj.list_folders()) [(('\\HasNoChildren',), '/', 'Drafts'), (('\\HasNoChildren',), '/', 'Filler'), (('\\HasNoChildren',), '/', 'INBOX'), (('\\HasNoChildren',), '/', 'Sent'), --snip -- (('\\HasNoChildren', '\\Flagged'), '/', '[Gmail]/Starred'), (('\\HasNoChildren', '\\Trash'), '/', '[Gmail]/Trash')]

如果你有一个Gmail账户，这就是输出可能的样子（Gmail将文件夹称为label，但它们的工作方式与文件夹相同）。每个元组的三个值，例如 (('\HasNoChildren',), '/', 'INBOX')，解释如下：

- 该文件夹的标志的元组（这些标志代表到底是什么超出了本书的讨论范围，你可以放心地忽略该字段）。

- 名称字符串中用于分隔父文件夹和子文件夹的分隔符。

- 该文件夹的全名。

要选择一个文件夹进行搜索，就调用IMAPClient对象的select_folder()方法，传入该文件夹的名称字符串。>>> imapObj.select_folder('INBOX', readonly=True)

可以忽略select_folder()的返回值。如果所选文件夹不存在，Python会抛出imaplib.error异常。

readonly=True关键字参数可以防止你在随后的方法调用中，不小心更改或删除该文件夹中的任何电子邮件。除非你想删除的电子邮件，否则将readonly设置为True总是个好主意。

### 16.4.5 执行搜索文件夹选中后，就可以用IMAPClient对象的search()方法搜索电子邮件。search()的参数是一个字符串列表，每一个格式化为IMAP搜索键。表16-3介绍了各种搜索键。

表16-3 IMAP搜索键搜索键含义

'ALL'

返回该文件夹中的所有邮件。如果你请求一个大文件夹中的所有消息，可能会遇到imaplib的大小限制。参见16.4.6小节"大小限制"

'BEFORE date ', 'ON date ', 'SINCE date '

这三个搜索键分别返回给定date之前、当天和之后IMAP服务器接收的消息。日期的格式必须像05-Jul-2015。此外，虽然'SINCE 05-Jul-2015'将匹配7月5日当天和之后的消息，但'BEFORE 05-Jul-2015'仅匹配7月5日之前的消息，不包括7月5日当天

'SUBJECT string ', 'BODY string ', 'TEXT string '

分别返回string出现在主题、正文、主题或正文中的消息。如果string中有空格，就使用双引号：'TEXT "search with spaces"'

'FROM string ', 'TO string ', 'CC string ', 'BCC string '

返回所有消息，其中string分别出现在"from"邮件地址，"to"邮件地址，"cc"（抄送）地址，或"bcc"（密件抄送）地址中。 如果string中有多个电子邮件地址，就用空格将它们分开，并使用双引号： 'CC "firstcc@example.com secondcc@example.com "'

'SEEN', 'UNSEEN'

分别返回包含和不包含\ Seen标记的所有信息。如果电子邮件已经被fetch()方法调用访问（稍后描述），或者你曾在电子邮件程序或网络浏览器中点击过它，就会有\ Seen标记。比较常用的说法是电子邮件"已读"，而不是"已看"，但它们的意思一样。

'ANSWERED', 'UNANSWERED'

分别返回包含和不包含\ Answered标记的所有消息。如果消息已答复，就会有\ Answered标记

'DELETED', 'UNDELETED'

分别返回包含和不包含\Deleted 标记的所有信息。用delete_messages()方法删除的邮件就会有\Deleted 标记，直到调用expunge()方法才会永久删除（请参阅16.4.10节"删除电子邮件"）。请注意，一些电子邮件提供商，例如Gmail，会自动清除邮件

'DRAFT', 'UNDRAFT'

分别返回包含和不包含\ Draft标记的所有消息。草稿邮件通常保存在单独的草稿文件夹中，而不是在收件箱中

'FLAGGED', 'UNFLAGGED'

分别返回包含和不包含\Flagged 标记的所有消息。这个标记通常用来标记电子邮件为"重要"或"紧急"

'LARGER N ', 'SMALLER N '

分别返回大于或小于N个字节的所有消息

'NOT search-key '

返回搜索键不会返回的那些消息

'OR search-key1 search-key2 '

返回符合第一个或第二个搜索键的消息请注意，在处理标志和搜索键方面，某些IMAP服务器的实现可能稍有不同。可能需要在交互式环境中试验一下，看看它们实际的行为如何。

在传入search()方法的列表参数中，可以有多个IMAP搜索键字符串。返回的消息将匹配所有的搜索键。如果想匹配任何一个搜索键，使用OR搜索键。对于NOT和OR搜索键，它们后边分别跟着一个和两个完整的搜索键。

下面是search()方法调用的一些例子，以及它们的含义：

imapObj.search (['ALL'] ) 返回当前选定的文件夹中的每一个消息。

imapObj.search (['ON 05-Jul-2015'] )返回在2015年7月5日发送的每个消息。

imapObj.search(['SINCE 01-Jan-2015', 'BEFORE 01-Feb-2015', 'UNSEEN']) 返回2015年1月发送的所有未读消息（注意，这意味着从1月1日直到2月1日，但不包括2月1日）。

imapObj.search(['SINCE 01-Jan-2015', 'FROM alice@example.com']) 返回自2015年开始以来，发自alice@example.com的消息。

imapObj.search(['SINCE 01-Jan-2015', 'NOT FROM alice@example.com']) 返回自2015年开始以来，除alice@example.com外，其他所有人发来的消息。

imapObj.search(['OR FROM alice@example.com FROM bob@example.com']) 返回发自alice@example.com或bob@example.com的所有信息。

imapObj.search(['FROM alice@example.com', 'FROM bob@example.com'])恶作剧例子！该搜索不会返回任何消息，因为消息必须匹配所有搜索关键词。因为只能有一个"from"地址，所以一条消息不可能既来自alice@example.com，又来自bob@example.com。

search()方法不返回电子邮件本身，而是返回邮件的唯一整数ID（UID）。然后，可以将这些UID传入fetch()方法，获得邮件内容。

输入以下代码，继续交互式环境的例子：>>> UIDs = imapObj.search(['SINCE 05-Jul-2015']) >>> UIDs [40032, 40033, 40034, 40035, 40036, 40037, 40038, 40039, 40040, 40041]

这里，search()返回的消息ID列表（针对7月5日以来接收的消息）保存在UIDs中。计算机上返回的UIDs列表与这里显示的不同，它们对于特定的电子邮件账户是唯一的。如果你稍后将UID传递给其他函数调用，请用你收到的UID值，而不是本书例子中打印的。

### 16.4.6 大小限制如果你的搜索匹配大量的电子邮件，Python可能抛出异常imaplib.error: got more than 10000 bytes。如果发生这种情况，必须断开并重连IMAP服务器，然后再试。

这个限制是防止Python程序消耗太多内存。遗憾的是，默认大小限制往往太小。可以执行下面的代码，将限制从10000字节改为10000000字节：>>> import imaplib >>> imaplib._MAXLINE = 10000000

这应该能避免该错误消息再次出现。也许要在你写的每一个IMAP程序中加上这两行。

### 16.4.7 取邮件并标记为已读得到UID的列表后，可以调用IMAPClient对象的fetch()方法，获得实际的电子邮件内容。

UID列表是fetch()的第一个参数。第二个参数应该是['BODY[]']，它告诉fetch()下载UID列表中指定电子邮件的所有正文内容。

使用IMAPClient的gmail_search()方法如果登录到imap.gmail.com服务器来访问Gmail账户，IMAPClient对象提供了一个额外的搜索函数，模拟Gmail网页顶部的搜索栏，如图16-1中高亮的部分所示。

图16-1 在Gmail网页顶部的搜索栏除了用IMAP搜索键搜索，可以使用Gmail更先进的搜索引擎。Gmail在匹配密切相关的单词方面做得很好（例如，搜索driving也会匹配drive和drove），并按照匹配的程度对搜索结果排序。也可以使用Gmail的高级搜索操作符（更多信息请参见http://nostarch.com/automatestuff/）。如果登录到Gmail账户，向gmail_search()方法传入搜索条件，而不是search()方法，就像下面交互式环境的例子：>>> UIDs = imapObj.gmail_search('meaning of life') >> UIDs [42]

啊，是的，那封电子邮件包含了生命的意义！我一直在期待。

让我们继续交互式环境的例子。>>> rawMessages = imapObj.fetch(UIDs, ['BODY[]']) >>> import pprint >>> pprint.pprint(rawMessages) {40040: {'BODY[]': 'Delivered-To: my_email_address@gmail.com\r\n' 'Received: by 10.76.71.167 with SMTP id ' --snip -- '\r\n' '------=_Part_6000970_707736290.1404819487066--\r\n', 'SEQ': 5430}}

导入 pprint，将 fetch()的返回值（保存在变量 rawMessages 中）传入pprint.pprint()，"漂亮打印"它。你会看到，这个返回值是消息的嵌套字典，其中以UID作为键。每条消息都保存为一个字典，包含两个键：'BODY[]'和'SEQ'。'BODY[]'键映射到电子邮件的实际正文。'SEQ'键是序列号，它与UID的作用类似。你可以放心地忽略它。

正如你所看到的，在'BODY[]'键中的消息内容是相当难理解的。这种格式称为RFC822，是专为IMAP服务器读取而设计的。但你并不需要理解RFC 822格式，本章稍后的pyzmail模块将替你来理解它。

如果你选择一个文件夹进行搜索，就用readonly=True关键字参数来调用select_ folder()。这样做可以防止意外删除电子邮件，但这也意味着你用fetch()方法获取邮件时，它们不会标记为已读。如果确实希望在获取邮件时将它们标记已读，就需要将readonly=False传入select_folder()。如果所选文件夹已处于只读模式，可以用另一个 select_folder()调用重新选择当前文件夹，这次用readonly=False关键字参数：>>> imapObj.select_folder('INBOX', readonly=False)

### 16.4.8 从原始消息中获取电子邮件地址对于只想读邮件的人来说，fetch()方法返回的原始消息仍然不太有用。pyzmail模块解析这些原始消息，将它们作为PyzMessage对象返回，使邮件的主题、正文、"收件人"字段、"发件人"字段和其他部分能用Python代码轻松访问。

用下面的代码继续交互式环境的例子（使用你自己的邮件账户的UID，而不是这里显示的）：>>> import pyzmail >>> message = pyzmail.PyzMessage.factory(rawMessages[40041]['BODY[]'])

首先，导入pyzmail。然后，为了创建一个电子邮件的PyzMessage对象，调用pyzmail.PeekMessage.factory()函数，并传入原始邮件的'BODY[]'部分。结果保存在message中。现在，message中包含一个PyzMessage对象，它有几个方法，可以很容易地获得的电子邮件主题行，以及所有发件人和收件人的地址。get_subject()方法将主题返回为一个简单字符串。get_addresses()方法针对传入的字段，返回一个地址列表。例如，该方法调用可能像这样：>>> message.get_subject() 'Hello!' >>> message.get_addresses('from') [('Edward Snowden', 'esnowden@nsa.gov')] >>> message.get_addresses('to') [(Jane Doe', 'my_email_address@gmail.com')] >>> message.get_addresses('cc') [] >>> message.get_addresses('bcc') []

请注意，get_addresses()的参数是'from'、'to'、'cc'或 'bcc'。get_addresses()的返回值是一个元组列表。每个元组包含两个字符串：第一个是与该电子邮件地址关联的名称，第二个是电子邮件地址本身。如果请求的字段中没有地址，get_addresses()返回一个空列表。在这里，'cc'抄送和'bcc'密件抄送字段都没有包含地址，所以返回空列表。

### 16.4.9 从原始消息中获取正文电子邮件可以是纯文本、HTML 或两者的混合。纯文本电子邮件只包含文本，而HTML电子邮件可以有颜色、字体、图像和其他功能，使得电子邮件看起来像一个小网页。如果电子邮件仅仅是纯文本，它的PyzMessage对象会将html_part属性设为None。同样，如果电子邮件只是HTML，它的PyzMessage对象会将text_part属性设为None。

否则，text_part或html_part将有一个get_payload()方法，将电子邮件的正文返回为bytes数据类型（bytes数据类型超出了本书的范围）。但是，这仍然不是我们可以使用的字符串。啊！最后一步对get_payload()返回的bytes值调用decode()方法。decode()方法接受一个参数：这条消息的字符编码，保存在text_part.charset或html_part.charset属性中。最后，这返回了邮件正文的字符串。

输入以下代码，继续交互式环境的例子：1. >>> message.text_part != None True >>> message.text_part.get_payload().decode(message.text_part.charset) 2. 'So long, and thanks for all the fish!\r\n\r\n-Al\r\n' 3. >>> message.html_part != None True 4. >>> message.html_part.get_payload().decode(message.html_part.charset) '< div dir="ltr">< div>So long, and thanks for all the fish!< br>< br>< /div>-Al < br>< /div>\r\n'

我们正在处理的电子邮件包含纯文本和HTML内容，因此保存在message中的PyzMessage对象的text_part和html_part属性不等于None1. 3. 。对消息的text_part调用get_payload()，然后在bytes值上调用decode()，返回电子邮件的文本版本的字符串2. 。对消息的html_part调用get_payload()和decode()，返回电子邮件的HTML版本的字符串4. 。

### 16.4.10 删除电子邮件要删除电子邮件，就向IMAPClient对象的delete_messages()方法传入一个消息UID的列表。这为电子邮件加上\Deleted标志。调用expunge()方法，将永久删除当前选中的文件夹中带\Deleted标志的所有电子邮件。请看下面的交互式环境的例子：1. >>> imapObj.select_folder('INBOX', readonly=False) 2. >>> UIDs = imapObj.search(['ON 09-Jul-2015']) >>> UIDs [40066] >>> imapObj.delete_messages(UIDs) 3. {40066: ('\\Seen', '\\Deleted')} >>> imapObj.expunge() ('Success', [(5452, 'EXISTS')])

这里，我们调用了IMAPClient对象的select_folder()方法，传入'INBOX'作为第一个参数，选择了收件箱。我们也传入了关键字参数readonly=False，这样我们就可以删除电子邮件1. 。我们搜索收件箱中的特定日期收到的消息，将返回的消息ID保存在UIDs中2. 。调用delete_message()并传入UIDs，返回一个字典，其中每个键值对是一个消息 ID 和消息标志的元组，它现在应该包含\Deleted标志3. 。然后调用expunge()，永久删除带\Deleted标志的邮件。如果清除邮件没有问题，就返回一条成功信息。请注意，一些电子邮件提供商，如Gmail，会自动清除用delete_messages()删除的电子邮件，而不是等待来自IMAP客户端的expunge命令。

### 16.4.11 从IMAP服务器断开如果程序已经完成了获取和删除电子邮件，就调用IMAPClient的logout()方法，从IMAP服务器断开连接。>>> imapObj.logout()

如果程序运行了几分钟或更长时间，IMAP服务器可能会超时，或自动断开。在这种情况下，接下来程序对IMAPClient对象的方法调用会抛出异常，像下面这样：imaplib.abort: socket error: [WinError 10054] An existing connection was forcibly closed by the remote host

在这种情况下，程序必须调用imapclient.IMAPClient()，再次连接。

哟！齐活了。要跳过很多圈圈，但你现在有办法让Python程序登录到一个电子邮件账户，并获取电子邮件。需要回忆所有步骤时，你可以随时参考16.4节"用IMAP获取和删除电子邮件"。

## 16.5 项目：向会员发送会费提醒电子邮件假定你一直"自愿"为"强制自愿俱乐部"记录会员会费。这确实是一项枯燥的工作，包括维护一个电子表格，记录每个月谁交了会费，并用电子邮件提醒那些没交的会员。不必你自己查看电子表格，而是向会费超期的会员复制和粘贴相同的电子邮件。你猜对了，让我们编写一个脚本，帮你完成任务。

在较高的层面上，下面是程序要做的事：

- 从Excel电子表格中读取数据。

- 找出上个月没有交费的所有会员。

- 找到他们的电子邮件地址，向他们发送针对个人的提醒。

这意味着代码需要做到以下几点：

- 用openpyxl模块打开并读取Excel文档的单元格（处理Excel文件参见第12章）。

- 创建一个字典，包含会费超期的会员。

- 调用smtplib.SMTP()、ehlo()、starttls()和login()，登录SMTP服务器。

- 针对会费超期的所有会员，调用sendmail()方法，发送针对个人的电子邮件提醒。

打开一个新的文件编辑器窗口，并保存为sendDuesReminders.py。

### 第1步：打开Excel文件假定用来记录会费支付的 Excel 电子表格看起来如图 16-2 所示，放在名为duesRecords.xlsx的文件中。可以从http://nostarch.com/automatestuff/下载该文件。

图16-2 记录会员会费支付电子表格该电子表格中包含每个成员的姓名和电子邮件地址。每个月有一列，记录会员的付款状态。在成员交纳会费后，对应的单元格就记为paid。

该程序必须打开duesRecords.xlsx，通过调用get_highest_column()方法，弄清楚最近一个月的列（可以参考第12章，了解用openpyxl模块访问Excel电子表格文件单元格的更多信息）。在文件编辑器窗口中输入以下代码： #! python3 # sendDuesReminders.py - Sends emails based on payment status in spreadsheet. import openpyxl, smtplib, sys # Open the spreadsheet and get the latest dues status. 1. wb = openpyxl.load_workbook('duesRecords.xlsx') 2. sheet = wb.get_sheet_by_name('Sheet1') 3. lastCol = sheet.get_highest_column() 4. latestMonth = sheet.cell(row=1, column=lastCol).value # TODO: Check each member's payment status. # TODO: Log in to email account. # TODO: Send out reminder emails.

导入openpyxl、smtplib和sys模块后，我们打开duesRecords.xlsx文件，将得到的Workbook对象保存在wb中1. 。然后，取得Sheet 1，将得到的Worksheet对象保存在sheet中2. 。既然有了Worksheet对象，就可以访问行、列和单元格。我们将最后一列保存在lastCol中3. ，然后用行号1和lastCol来访问应该记录着最近月份的单元格。取得该单元格的值，并保存在latestMonth 中4. 。

### 第2步：查找所有未付成员一旦确定了最近一个月的列数（保存在lastCol中），就可以循环遍历第一行（这是列标题）之后的所有行，看看哪些成员在该月会费的单元格中写着paid。如果会员没有支付，就可以从列1和2中分别抓取成员的姓名和电子邮件地址。这些信息将放入unpaidMembers字典，它记录最近一个月没有交费的所有成员。将以下代码添加到sendDuesReminder.py中。 #! python3 # sendDuesReminders.py - Sends emails based on payment status in spreadsheet. --snip -- # Check each member's payment status.unpaidMembers = {} 1. for r in range(2, sheet.get_highest_row() + 1): 2. payment = sheet.cell(row=r, column=lastCol).value if payment != 'paid': 3. name = sheet.cell(row=r, column=1).value 4. email = sheet.cell(row=r, column=2).value 5. unpaidMembers[name] = email

这段代码设置了一个空字典unpaidMembers，然后循环遍历第一行之后所有的行1. 。对于每一行，最近月份的值保存在payment中2. 。如果payment不等于'paid'，则第一列的值保存在name中3. ，第二列的值保存在email中4. ，name和email添加到unpaidMembers中5. 。

### 第3步：发送定制的电子邮件提醒得到所有未付费成员的名单后，就可以向他们发送电子邮件提醒了。将下面的代码添加到程序中，但要代入你的真实电子邮件地址和提供商的信息：

#! python3 # sendDuesReminders.py - Sends emails based on payment status in spreadsheet. --snip -- # Log in to email account.smtpObj = smtplib.SMTP('smtp.gmail.com', 587)smtpObj.ehlo()smtpObj.starttls()smtpObj.login('my_email_address@gmail.com ', sys.argv[1])

调用smtplib.SMTP()并传入提供商的域名和端口，创建一个SMTP对象。调用ehlo()和starttls()，然后调用login()，并传入你的电子邮件地址和sys.argv[1]，其中保存着你的密码字符串。在每次运行程序时，将密码作为命令行参数输入，避免在源代码中保存密码。

程序登录到你的电子邮件账户后，就应该遍历unpaidMembers字典，向每个会员的电子邮件地址发送针对个人的电子邮件。将以下代码添加到sendDuesReminders.py： #! python3 # sendDuesReminders.py - Sends emails based on payment status in spreadsheet. --snip -- # Send out reminder emails.for name, email in unpaidMembers.items(): 1. body = "Subject: %s dues unpaid.\nDear %s,\nRecords show that you have notpaid dues for %s. Please make this payment as soon as possible. Thank you!'" %(latestMonth, name, latestMonth) 2. print('Sending email to %s...' % email) 3. sendmailStatus = smtpObj.sendmail('my_email_address@gmail.com ', email, body) 4. if sendmailStatus != {}: print('There was a problem sending email to %s: %s' % (email, sendmailStatus))smtpObj.quit()

这段代码循环遍历unpaidMembers中的姓名和电子邮件。对于每个没有付费的成员，我们用最新的月份和成员的名称，定制了一条消息，并保存在body中1. 。我们打印输出，表示正在向这个会员的电子邮件地址发送电子邮件2. 。然后调用sendmail()，向它传入地址和定制的消息3. 。返回值保存在sendmailStatus中。

回忆一下，如果SMTP服务器在发送某个电子邮件时报告错误，sendmail()方法将返回一个非空的字典值。for循环最后部分在4. 行检查返回的字典是否非空，如果非空，则打印收件人的电子邮件地址以及返回的字典。

程序完成发送所有电子邮件后，调用quit()方法，与SMTP服务器断开连接。

如果运行该程序，输出会像这样：Sending email to alice@example.com... Sending email to bob@example.com... Sending email to eve@example.com...

收件人将收到如图16-3所示的电子邮件。

图16-3 从sendDuesReminders.py自动发送的电子邮件

## 16.6 用Twilio发送短信大多数人更可能靠近自己的手机，而不是自己的电脑，所以与电子邮件相比，短信发送通知可能更直接、可靠。此外，短信的长度较短，让人更有可能阅读它们。

在本节中，你将学习如何注册免费的Twilio服务，并用它的Python模块发送短信。Twilio是一个SMS网关服务，这意味着它是一种服务，让你通过程序发送短信。虽然每月发送多少短信会有限制，并且文本前面会加上Sent from a Twilio trial account，但这项试用服务也许能满足你的个人程序。免费试用没有限期，不必以后升级到付费的套餐。

Twilio不是唯一的SMS网关服务。如果你不喜欢使用Twilio，可以在线搜索free sms gateway、python sms api，甚至twilio alternatives，寻找替代服务。

注册Twilio账户之前，先安装twilio模块。附录A详细介绍了如何安装第三方模块。

本节特别针对美国。Twilio 确实也在美国以外的国家提供手机短信服务，本书并不包括这些细节。但twilio 模块及其功能，在美国以外的国家也能用。更多信息请参见http://twilio.com/。

### 16.6.1 注册Twilio账号访问http://twilio.com/并填写注册表单。注册了新账户后，你需要验证一个手机号码，短信将发给该号码（这项验证是必要的，防止有人利用该服务向任意的手机号码发送垃圾短信）。

收到验证号码短信后，在Twilio网站上输入它，证明你拥有要验证的手机。现在，就可以用twilio模块向这个电话号码发送短信了。

Twilio提供的试用账户包括一个电话号码，它将作为短信的发送者。你将需要两个信息：你的账户SID和AUTH（认证）标志。在登录Twilio账户时，可以在Dashboard页面上找到这些信息。从Python程序登录时，这些值将作为你的Twilio用户名和密码。

### 16.6.2 发送短信一旦安装了twilio模块，注册了Twilio账号，验证了你的手机号码，登记了Twilio电话号码，获得了账户的SID和auth标志，你就终于准备好通过Python脚本向你自己发短信了。

与所有的注册步骤相比，实际的Python代码很简单。保持计算机连接到因特网，在交互式环境中输入以下代码，用你的真实信息替换accountSID、authToken、myTwilioNumber和myCellPhone变量的值：1. >>> from twilio.rest import TwilioRestClient >>> accountSID = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ' >>> authToken = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ' 2. >>> twilioCli = TwilioRestClient(accountSID, authToken) >>> myTwilioNumber = '+14955551234' >>> myCellPhone = '+14955558888' 3. >>> message = twilioCli.messages.create(body='Mr. Watson - Come here - I wantto see you.', from_=myTwilioNumber, to=myCellPhone)

键入最后一行后不久，你会收到一条短信，内容为：Sent from your Twilio trial account - Mr. Watson - Come here - I want to see you.。

因为twilio模块的设计方式，导入它时需要使用from twilio.rest import TwilioRestClient，而不仅仅是import twilio1. 。将账户的SID保存在accountSID，认证标志保存在authToken中，然后调用TwilioRestClient()，并传入accountSID和authToken。TwilioRestClient()调用返回一个TwilioRestClient对象2. 。该对象有一个message属性，该属性又有一个create()方法，可以用来发送短信。正是这个方法，将告诉Twilio的服务器发送短信。将你的Twilio号码和手机号码分别保存在myTwilioNumber和myCellPhone中，然后调用create()，传入关键字参数，指明短信的正文、发件人的号码（myTwilioNumber），以及收信人的电话号码（myCellPhone）3.

create()方法返回的Message对象将包含已发送短信的相关信息。输入以下代码，继续交互式环境的例子：>>> message.to '+14955558888' >>> message.from _ '+14955551234' >>> message.body 'Mr. Watson - Come here - I want to see you.'

to、from和body属性应该分别保存了你的手机号码、Twilio号码和消息。请注意，发送手机号码是在from 属性中，末尾有一个下划线，而不是from。这是因为from是一个Python关键字（例如，你在from modulename import *形式的import语句中见过它），所以它不能作为一个属性名。输入以下代码，继续交互式环境的例子：>>> message.status 'queued' >>> message.date_created datetime.datetime(2015, 7, 8, 1, 36, 18) >>> message.date_sent == None True

status 属性应该包含一个字符串。如果消息被创建和发送，date_created 和date_sent属性应该包含一个datetime对象。如果已收到短信，而status属性却设置为'queued'，date_sent属性设置为None，这似乎有点奇怪。这是因为你先将Message对象记录在message变量中，然后短信才实际发送。你需要重新获取Message对象，查看它最新的status和date_sent。每个Twilio消息都有唯一的字符串ID（SID），可用于获取Message对象的最新更新。输入以下代码，继续交互式环境的例子： >>> message.sid 'SM09520de7639ba3af137c6fcb7c5f4b51' 1. >>> updatedMessage = twilioCli.messages.get(message.sid) >>> updatedMessage.status 'delivered' >>> updatedMessage.date_sent datetime.datetime(2015, 7, 8, 1, 36, 18)

输入message.sid将显示这个消息的SID。将这个SID传入Twilio客户端的get()方法1. ，你可以取得一个新的Message对象，包含最新的信息。在这个新的Message对象中，status和date_sent属性是正确的。

status属性将设置为下列字符串之一：'queued'、'sending'、'sent'、'delivered'、'undelivered'或'failed'。这些状态不言自明，但对于更准确的细节，请查看http://nostarch. com/automatestuff/的资源。

用Python接收短信遗憾的是，用Twilio接收短信比发送短信更复杂一些。Twilio需要你有一个网站，运行自己的Web应用程序。这已超出了本书的范围，但你可以在本书的资源中找到更多细节（http://nostarch.com/automatestuff/）。

## 16.7 项目："只给我发短信"模块最常用你的程序发短信的人可能就是你。当你远离计算机时，短信是通知你自己的好方式。如果你已经用程序自动化了一个无聊的任务，它需要运行几小时，你可以在它完成时，让它用短信通知你。或者可以定期运行某个程序，它有时需要与你联系，例如天气检查程序，用短信提醒你带伞。

举一个简单的例子，下面是一个Python小程序，包含了textmyself()函数，它将传入的字符串参数作为短信发出。打开一个新的文件编辑器窗口，输入以下代码，用自己的信息替换帐户SID，认证标志和电话号码。将它保存为textMyself.py。 #! python3 # textMyself.py - Defines the textmyself() function that texts a message # passed to it as a string. # Preset values: accountSID = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ' authToken = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ' myNumber = '+15559998888' twilioNumber = '+15552225678' from twilio.rest import TwilioRestClient 1. def textmyself(message): 2. twilioCli = TwilioRestClient(accountSID, authToken) 3. twilioCli.messages.create(body=message, from_=twilioNumber, to=myNumber)

该程序保存了账户的SID、认证标志、发送号码及接收号码。然后它定义了textmyself()，接收参数1. ，创建TwilioRestClient对象2. ，并用你传入的消息调用create()3. 。

如果你想让其他程序使用textmyself()函数，只需将textMyself.py文件和Python的可执行文件放在同一个文件夹中（Windows上是C:\Python34，OS X上是/usr/local/lib/python3.4，Linux上是/usr/bin/python3）。现在，你可以在其他程序中使用该函数。只要想在程序中发短信给你，就添加以下代码：import textmyself textmyself.textmyself('The boring task is finished.')

注册Twilio和编写短信代码只要做一次。在此之后，从任何其他程序中发短信，只要两行代码。

## 16.8 小结通过因特网和手机网络，我们用几十种不同的方式相互通信，但以电子邮件和短信为主。你的程序可以通过这些渠道沟通，这给它们带来强大的新通知功能。甚至可以编程运行在不同的计算机上，相互直接通过电子邮件能信，一个程序用SMTP发送电子邮件，另一个用IMAP收取。

Python 的 smtplib 提供了一些函数，利用 SMTP，通过电子邮件提供商的SMTP服务器发送电子邮件。同样，第三方的imapclient和pyzmail模块让你访问IMAP服务器，并取回发送给你的电子邮件。虽然IMAP比SMTP复杂一些，但它也相当强大，允许你搜索特定电子邮件、下载它们、解析它们，提取主题和正文作为字符串值。

短信与电子邮件有点不同，因为它不像电子邮件，发送短信不仅需要互联网连接。好在，像Twilio这样的服务提供了模块，允许你通过程序发送短信。一旦通过了初始设置过程，就能够只用几行代码来发送短信。掌握了这些模块，就可以针对特定的情况编程，在这些情况下发送通知或提醒。现在，你的程序将超越运行它们的计算机！

## 16.9 习题

1．发送电子邮件的协议是什么？检查和接收电子邮件的协议是什么？

2．必须调用哪4个smtplib函数/方法，才能登录到SMTP服务器？

3．必须调用哪两个imapclient函数/方法，才能登录到IMAP服务器？

4．传递给mapObj.search()什么样的参数？

5．如果你的代码收到了错误消息，got more than 10000 bytes，你该怎么做？

6．imapclient模块负责连接到IMAP服务器和查找电子邮件。什么模块负责读取imapclient收集的电子邮件？

7．在发送短信之前，你需要从Twilio得到哪3种信息？

## 16.10 实践项目作为实践，编程完成以下任务。

### 16.10.1 随机分配家务活的电子邮件程序编写一个程序，接受一个电子邮件地址的列表，以及一个需要做的家务活列表，并随机将家务活分配给他们。用电子邮件通知每个人分配给他们的家务。如果你觉得需要挑战，就记录每个人之前分配家务活的记录，这样就可以确保程序不会向任何人分配上一次同样的家务活。另一个可能的功能，就是安排程序每周自动运行一次。

这里有一个提示：如果将一个列表传入random.choice()函数，它将从该列表中返回一个随机选择的项。你的部分代码看起来可能像这样：chores = ['dishes', 'bathroom', 'vacuum', 'walk dog'] randomChore = random.choice(chores) chores.remove(randomChore) # this chore is now taken, so remove it

### 16.10.2 伞提醒程序第11章展示了如何利用requests模块，从http://weather.gov/ 抓取数据。编写一个程序，在你早晨快醒来时运行，检查当天是否会下雨。如果会下雨，让程序用短信提醒你出门之前带好一把伞。

### 16.10.3 自动退订编程扫描你的电子邮件账户，在所有邮件中找到所有退订链接，并自动在浏览器中打开它们。该程序必须登录到你的电子邮件服务提供商的IMAP服务器，并下载所有电子邮件。可以用BeautifulSoup（在第11章中介绍）检查所有出现unsubscribe（退订）的HTML链接标签。

得到这些URL的列表后，可以用webbrowser.open()，在浏览器中自动打开所有这些链接。

仍然需要手工操作并完成所有额外的步骤，从这些邮件列表中退订。在大多数情况下，这需要点击一个链接确认。

但这个脚本让你不必查看所有电子邮件，寻找退订链接。然后，可以将这个脚本转给你的朋友，让他们能够针对他们的电子邮件账户运行它（要确保你的邮箱密码没有硬编码在源代码中）。

### 16.10.4 通过电子邮件控制你的电脑编写一个程序，每15分钟检查电子邮件账户，获取用电子邮件发送的所有指令，并自动执行这些指令。例如，BitTorrent是一个对等网络下载系统。利用免费的BitTorrent软件，如qBittorrent，可以在家用电脑上下载很大的媒体文件。如果你用电子邮件向该程序发送一个（完全合法的，根本不是盗版的）BitTorrent链接，该程序将检查电子邮件，发现这个消息，提取链接，然后启动qBittorrent，开始下载文件。通过这种方式，你可以在离开家的时候让家用电脑开始下载，这些（完全合法的，根本不是盗版的）下载在你回家前就能完成。

第15章介绍了如何利用subprocess.Popen()函数启动计算机上的程序。例如，下面的调用将启动qBittorrent程序，并打开一个torrent文件：qbProcess = subprocess.Popen(['C:\\Program Files (x86)\\qBittorrent\\ qbittorrent.exe', 'shakespeare_complete_works.torrent'])

当然，你希望该程序确保邮件来自于你自己。具体来说，你可能希望该邮件包含一个密码，因为在电子邮件中伪造"from"地址，对黑客来说很容易。该程序应该删除它发现的邮件，这样就不会每次检查电子邮件账户时重复执行命令。作为一个额外的功能，让程序每次执行命令时，用电子邮件或短信给你发一条确认信息。因为该程序运行时，你不会坐在运行它的计算机前面，所以利用日志函数（参见第 10章）写文本文件日志是一个好主意，你可以检查是否发生错误。

qBittorrent（以及其他BitTorrent应用程序）有一个功能，下载完成后，它可以自动退出。第15章解释了如何用Popen对象的wait()方法，确定启动的应用程序何时已经退出。wait()方法调用将阻塞，直到qBittorrent停止，然后程序可以通过电子邮件或短信，通知你下载已经完成。

可以为这个项目添加许多可能的功能。如果遇到困难，可以从 http://nostarch. com/automatestuff/下载这个程序的示例实现。

# 第18章用GUI自动化控制键盘和鼠标知道用于编辑电子表格、下载文件和运行程序的各种Python模块，是很有用的。但有时候，就是没有模块对应你要操作的应用程序。在计算机上自动化任务的终极工具，就是写程序直接控制键盘和鼠标。这些程序可以控制其他应用，向它们发送虚拟的击键和鼠标点击，就像你自己坐在计算机前与应用交互一样。这种技术被称为"图形用户界面自动化"，或简称为"GUI自动化"。有了GUI自动化，你的程序就像一个活人用户坐在计算机前一样，能做任何事情，除了将咖啡泼在键盘上。

请将GUI自动化看成是对一个机械臂编程。你可以对机械臂编程，让它敲键盘或移动鼠标。对于涉及许多无脑点击或填表的任务，这种技术特别有用。

pyautogui模块包含了一些函数，可以模拟鼠标移动、按键和滚动鼠标滚轮。本章只介绍了pyautogui功能的子集。可以在http://pyautogui.readthedocs.org/ 找到完整的文档。

## 18.1 安装pyautogui模块

pyautogui模块可以向Windows、OS X和Linux发送虚拟按键和鼠标点击。根据你使用的操作系统，在安装pyautogui之前，可能需要安装一些其他模块（称为依赖关系）。

- 在Windows上，不需要安装其他模块。

- 在OS X上，运行sudo pip3 install pyobjc-framework-Quartz，sudo pip3 install pyobjc-core，然后sudo pip3 install pyobjc。

- 在Linux上，运行sudo pip3 install python3-xlib，sudo apt-get install scrot，sudo apt-get install python3-tk，以及sudo apt-get install python3-dev（Scrot是PyAutoGUI使用的屏幕快照程序）。

在这些依赖安装后，运行pip install pyautogui（或在OS X和Linux上运行pip3），安装pyautogui。

附录A有安装第三方模块的完整信息。要测试PyAutoGUI是否正确安装，就在交互式环境运行import pyautogui，并检查出错信息。

## 18.2 走对路在开始GUI自动化之前，你应该知道如何避免可能发生的问题。Python能以想象不到的速度移动鼠标并击键。实际上，它可能太快，导致其他程序跟不上。而且，如果出了问题，但你的程序继续到处移动鼠标，可能很难搞清楚程序到底在做什么，或者如何从问题中恢复。就像迪斯尼电影《魔法师的学徒》中的魔法扫帚，它不断地向米老鼠的浴缸注水（然后水溢出来），你的程序可能失去控制，即使它完美地执行你的指令。如果程序自己在移动鼠标，停止它可能很难，你不能点击IDLE窗口来关闭它。好在，有几种方法来防止或恢复GUI自动化问题。

### 18.2.1 通过注销关闭所有程序停止失去控制的GUI自动化程序，最简单的方法可能是注销，这将关闭所有运行的程序。在Windows和Linux上，注销的热键是Ctrl-Alt-Del。在OS X，热键是⌘-Shift-Option-Q。通过注销，你会丢失所有未保存的工作，但至少不需要等计算机完全重启。

### 18.2.2 暂停和自动防故障装置你可以告诉脚本在每次函数调用后等一会儿，在出问题的时候，让你有很短的时间窗口来控制鼠标和键盘。要做到这一点，将pyautogui.PAUSE变量设置为要暂停的秒数。例如，在设置pyautogui.PAUSE = 1.5之后，每个PyAutoGUI函数调用在执行动作之后，都会等待一秒半。非PyAutoGUI指令不会停顿。

pyautogui 也有自动防故障功能。将鼠标移到屏幕的左上角，这将导致pyautogui产生pyautogui .FailSafeException异常。你的程序可以用try和except语句来处理这个异常，也可以让异常导致程序崩溃。这两种情况下，如果你尽可能快地向左上移动鼠标，自动防故障功能都将停止程序。可以设置pyautogui. FAILSAFE = False，禁止这项功能。在交互式环境中输入以下内容：>>> import pyautogui >>> pyautogui.PAUSE = 1 >>> pyautogui.FAILSAFE = True

这里我们导入pyautogui，并将pyautogui.PAUSE设置为1，即每次函数调用后暂停一秒。将pyautogui.FAILSAFE设置为True，启动自动防故障功能。

## 18.3 控制鼠标移动在本节中，你将学习如何利用pyautogui移动鼠标，追踪它在屏幕上的位置，但首先需要理解pyautogui如何处理坐标。

pyautogui的鼠标函数使用x、y坐标。图18-1中展示了计算机屏幕的坐标系统。它与17章中讨论的图像坐标系统类似。原点的x、y都是零，在屏幕的左上角。向右x坐标增加，向下y坐标增加。所有坐标都是正整数，没有负数坐标。

图18-1 分辨率为1920 × 1080的计算机屏幕上的坐标分辨率是屏幕的宽和高有多少像素。如果屏幕的分辨率设置为1920 × 1080，那么左上角的坐标是（0，0），右下角的坐标是（1919，1079）。

pyautogui.size() 函数返回两个整数的元组，包含屏幕的宽和高的像素数。在交互式环境中输入下面内容：>>> import pyautogui >>> pyautogui.size() (1920, 1080) >>> width, height = pyautogui.size()

在分辨率为1920 × 1080的计算机上，pyautogui.size() 返回（1920，1080）。根据屏幕分辨率的不同，返回值可能不一样。你可以将来自pyautogui.size() 的宽和高存在变量中，如width和height，让程序的可读性更好。

### 18.3.1 移动鼠标既然你理解了屏幕坐标，就让我们来移动鼠标。pyautogui.moveTo() 函数将鼠标立即移动到屏幕的指定位置。表示x、y坐标的整数值分别构成了函数的第一个和第二个参数。可选的duration整数或浮点数关键字参数，指定了将鼠标移到目的位置所需的秒数。如果不指定，默认值是零，表示立即移动（在PyAutoGUI函数中，所有的duration关键字参数都是可选的）。在交互式环境中输入以下内容：>>> import pyautogui >>> for i in range(10):pyautogui.moveTo(100, 100, duration=0.25)pyautogui.moveTo(200, 100, duration=0.25)pyautogui.moveTo(200, 200, duration=0.25)pyautogui.moveTo(100, 200, duration=0.25)

这个例子根据提供的坐标，以正方形的模式顺时针移动鼠标，移动了10次。每次移动耗时0.25秒，因为有关键字参数指定 duration=0.25。如果没有指定函数调用的第三个参数，鼠标就会马上从一个点移到另一个点。

pyautogui.moveRel() 函数相对于当前的位置移动鼠标。下面的例子同样以正方形的模式移动鼠标，只是它从代码开始运行时鼠标所在的位置开始，按正方形移动：>>> import pyautogui >>> for i in range(10):pyautogui.moveRel(100, 0, duration=0.25)pyautogui.moveRel(0, 100, duration=0.25)pyautogui.moveRel(-100, 0, duration=0.25)pyautogui.moveRel(0, -100, duration=0.25)

pyautogui.moveRel() 也接受3个参数：向右水平移动多少个像素，向下垂直移动多少个像素，以及（可选的）花多少时间完成移动。为第一第二个参数提供负整数，鼠标将向左或向上移动。

### 18.3.2 获取鼠标位置通过调用pyautogui.position() 函数，可以确定鼠标当前的位置。它将返回函数调用时，鼠标x、y坐标的元组。在交互式环境中输入以下内容，每次调用后请移动鼠标：>>> pyautogui.position() (311, 622) >>> pyautogui.position() (377, 481) >>> pyautogui.position() (1536, 637)

当然，返回值取决于鼠标的位置。

## 18.4 项目："现在鼠标在哪里？"

能够确定鼠标的位置，对于建立GUI自动化脚本是很重要的。但光看屏幕，几乎不能弄清楚像素的准确坐标。如果有一个程序在移动鼠标时随时显示 x y坐标，就会很方便。

总的来说，你希望该程序做到：

- 获得鼠标当前的xy坐标。

- 当鼠标在屏幕上移动时，更新这些坐标。

这意味着代码需要做到下列事情：

- 调用函数取得当前坐标。

- 在屏幕上打印回退字符。删除以前打印的坐标。

- 处理异常。让用户能按键退出。

打开一个新的文件编辑器窗口，将它保存为mouseNow.py。

### 第1步：导入模块程序开始是这样的：

#! python3 # mouseNow.py - Displays the mouse cursor's current position. import pyautogui print('Press Ctrl-C to quit.') #TODO: Get and print the mouse coordinates.

程序开始导入了pyautogui模块，打印的内容提醒用户按Ctrl-C退出。

### 第2步：编写退出代码和无限循环可以用无限 while 循环，不断打印通过mouse.position() 获得的当前鼠标坐标。对于退出程序的代码，你需要捕捉 KeyboardInterrupt 异常，它会在用户按下 Ctrl-C 时抛出。如果不处理这个异常，它会向用户显示丑陋的调用栈和出错信息。将下面内容添加到程序中：

#! python3 # mouseNow.py - Displays the mouse cursor's current position. import pyautogui print('Press Ctrl-C to quit.') try:while True:# TODO: Get and print the mouse coordinates. 1. except KeyboardInterrupt: 2. print('\nDone.')

为了处理这个异常，将无限while循环放在一个try语句中。当用户按下Ctrl-C，程序执行将转到except子句1. ，新行中将输出Done2. 。

### 第3步：获取并打印鼠标坐标

while循环内的代码应该获取当前鼠标的坐标，提供好看的格式，并打印输出。在while循环内添加以下代码：

#! python3 # mouseNow.py - Displays the mouse cursor's current position. import pyautogui print('Press Ctrl-C to quit.') --snip -- # Get and print the mouse coordinates.x, y = pyautogui.position()positionStr = 'X: ' + str(x).rjust(4) + ' Y: ' + str(y).rjust(4) --snip --

利用多重赋值的技巧，变量x、y得到了pyautogui.position() 返回元组中的两个整型值。将x、y传递给str() 函数，可以得到整型坐标的字符串形式。rjust() 字符串方法将对坐标右调整，让它们占据同样的宽度，不论坐标是一位、两位、三位或四位数字。连接右调准的字符串坐标，加上 'X: ' 和 ' Y: ' 标签，就得到了格式化好的字符串，保存在positionStr中。

在程序的末尾，添加以下代码：

#! python3 # mouseNow.py - Displays the mouse cursor's current position. --snip -- print(positionStr, end='') 1. print('\b' * len(positionStr), end='', flush=True)

这将在屏幕上打印positionStr。print() 函数的关键字参数end='' 阻止了在打印行末添加默认的换行字符。这可能会擦除你已经在屏幕上打印的文本，但只是最近一行文本。如果你先打印了一个换行字符，就不会擦除以前打印的内容。

要擦除文本，就打印\b 退格转义字符。这个特殊字符擦除屏幕当前行末尾的字符。代码行1. 利用字符串复制，得到了许多\b 字符构成的字符串，长度与positionStr中保存的字符串长度一样，效果就是擦除了前面打印的字符串。

print() 调用打印\b退格键字符时，总是传入flush=True（其技术上的理由超出了本书的范围）。否则，屏幕可能不会按期望更新。

while循环重复非常快，用户实际上不会注意到你在屏幕上删除并重新打印整个数字。例如，如果x坐标是563，鼠标右移一个像素，看起来就像563中的3变成了4。

如果运行程序，只有两行打印输出。看起来像这样：Press Ctrl-C to quit. X: 290 Y: 424

第一行显示指令：按Ctrl-C退出。第二行显示鼠标坐标，当你在屏幕上移动鼠标时，会变化。利用这个程序，就能搞清楚鼠标坐标，用于你的GUI自动化脚本。

## 18.5 控制鼠标交互既然你知道了如何移动鼠标，弄清楚了它在屏幕上的位置，就可以开始点击、拖动和滚动鼠标。

### 18.5.1 点击鼠标要向计算机发送虚拟的鼠标点击，就调用pyautogui.click() 方法。默认情况下，点击将使用鼠标左键，点击发生在鼠标当前所在位置。如果希望点击在鼠标当前位置以外的地方发生，可以传入x、y坐标作为可选的第一第二参数。

如果想指定鼠标按键，就加入button关键字参数，值分别为 'left'、'middle'或 'right'。例如，pyautogui.click（100，150，button='left'）将在坐标（100，150）处点击鼠标左键。而pyautogui.click（200，250，button='right'）将在坐标（200，250）处点击右键。

在交互式环境中输入以下内容：>>> import pyautogui >>> pyautogui.click(10, 5)

你应该看到鼠标移到屏幕左上角的位置，并点击一次。完整的"点击"是指按下鼠标按键，然后放开，同时不移动位置。实现点击也可以调用pyautogui. mouseDown()，这只是按下鼠标按键，再调用pyautogui.mouseUp()，这只是释放鼠标按键。这些函数的参数与click() 相同。实际上，click() 函数只是这两个函数调用的方便封装。

为了进一步方便，pyautogui.doubleClick() 函数只执行双击鼠标左键。pyautogui.rightClick() 和pyautogui.middleClick() 函数将分别执行双击右键和双击中键。

### 18.5.2 拖动鼠标

"拖动"意味着移动鼠标，同时按住一个按键不放。例如，可以通过拖动文件图标，在文件夹之间移动文件，或在日历应用中移动预约。

PyAutoGUI提供了pyautogui.dragTo() 和pyautogui.dragRel() 函数，将鼠标拖动到一个新的位置，或相对当前位置的位置。dragTo() 和dragRel() 的参数与moveTo() 和moveRel() 相同：x坐标/水平移动，y坐标/垂直移动，以及可选的时间间隔（在OS X上，如果鼠标移动太快，拖动会不对，所以建议提供duration关键字参数）。

要尝试这些函数，请打开一个绘图应用，如Windows上的Paint，OS X上的Paintbrush，或Linux上的GNU Paint（如果没有绘图应用，可以使用在线绘图，网址是http://sumopaint.com/ ）。我将使用PyAutoGUI在这些应用中绘图。

让鼠标停留在绘图应用的画布上，同时选中铅笔或画笔工具，在新的文件编辑窗口中输入以下内容，保存为spiralDraw.py：import pyautogui, time 1. time.sleep(5) 2. pyautogui.click() # click to put drawing program in focus distance = 200 while distance > 0: 3. pyautogui.dragRel(distance, 0, duration=0.2) # move right 4. distance = distance - 5 5. pyautogui.dragRel(0, distance, duration=0.2) # move down 5. pyautogui.dragRel(-distance, 0, duration=0.2) # move left distance = distance - 5 pyautogui.dragRel(0, -distance, duration=0.2) # move up

在运行这个程序时，会有5秒钟的延迟1. ，让你选中铅笔或画笔工具，并让鼠标停留在画图工具的窗口上。然后spiralDraw.py将控制鼠标，点击画图程序获得焦点2. 。如果窗口有闪烁的光标，它就获得了"焦点"，这时你的动作（例如打字，或这个例子中的拖动鼠标），就会影响该窗口。画图程序获取焦点后，spiralDraw.py将绘制一个正方形旋转图案，如图18-2所示。

图18-2 pyautogui.dragRel() 例子的结果

distance 变量从 200 开始，所以在 while 循环的第一次迭代中，第一次dragRel() 调用将光标向右拖动200像素，花了0.2秒3. 。然后distance降到1954. ，第二次dragRel() 调用将光标向下拖动195像素5. 。第三次dragRel() 调用将光标水平拖动−195（向左195）6. ，distance降到190，最后一次dragRel调用将光标向上拖动190。每次迭代，鼠标都向右、向下、向左、向上拖动，distance都比前一次迭代小一点。通过这段代码循环，就可以移动鼠标光标，画出正方形旋转图案。

可以手工画出这个漩涡（或者说用鼠标），但一定要画得很慢，才能这么精确。pyautogui能够几秒钟就画完。

注意你可以在代码中使用pillow模块的画图函数，画出这个图形，更多信息请参见第17章。但利用GUI自动化就能使用画图程序提供的高级画图工具，如灰度、不同的画笔或填充工具。

### 18.5.3 滚动鼠标最后一个pyautogui鼠标函数是scroll()。你向它提供一个整型参数，说明向上或向下滚动多少单位。单位的意义在每个操作系统和应用上不一样，所以你必须试验，看看在你的情况下滚动多远。滚动发生在鼠标的当前位置。传递正整数表示向上滚动，传递负整数表示向下滚动。将鼠标停留在IDLE窗口上，在IDLE的交互式环境中运行以下代码：>>> pyautogui.scroll(200)

你会看到IDLE轻松地向上滚动，然后又向下滚回来。发生向下滚动是因为，在执行完指令后，IDLE自动向下滚动到底部。输入以下代码作为替代：>>> import pyperclip >>> numbers = '' >>> for i in range(200): numbers = numbers + str(i) + '\n' >>> pyperclip.copy(numbers)

这导入了pyperclip，并建立一个空字符串numbers。代码然后循环200个数字，将每个数字和换行符加入numbers。在pyperclip.copy（numbers）之后，剪贴板中将保存200行数字。打开一个新的文件编辑窗口，将文本粘贴进去。这将得到一个很大的文本窗口，让你尝试滚动。在交互式环境中输入以下代码：>>> import time, pyautogui >>> time.sleep(5); pyautogui.scroll(100)

在第二行，输入的两条命令以分号分隔，这告诉Python在运行这些命令时，就像它们在独立的行中一样。唯一的区别在于，交互式环境不会在两个命令之间提示你输入。这对于这个例子很重要，因为我们希望pyautogui.scroll() 调用在等待之后自动发生（请注意，虽然在交互式环境中，将两条命令放在一行中可能有用，但在你的程序中，还是应该让每条命令独占一行）。

按下回车运行代码后，你有5秒钟的时间点击文件编辑窗口，让它获得焦点。在5秒钟的延迟结束后，pyautogui.scroll() 调用将导致文件编辑窗口向上滚动。

## 18.6 处理屏幕你的GUI自动化程序没有必要盲目地点击和输入。pyautogui拥有屏幕快照的功能，可以根据当前屏幕的内容创建图形文件。这些函数也可以返回一个Pillow的Image对象，包含当前屏幕的内容。如果你是跳跃式地阅读本书，可能需要阅读第17章，安装pillow模块，然后再继续本节的内容。

在Linux计算机上，需要安装scrot程序，才能在pyautogui中使用屏幕快照功能。在终端窗口中，执行sudo apt-get install scrot，安装该程序。如果你使用Windows或OS X，就跳过这一步，继续本节的内容。

### 18.6.1 获取屏幕快照要在Python中获取屏幕快照，就调用pyautogui.screenshot() 函数。在交互式环境中输入以下内容：>>> import pyautogui >>> im = pyautogui.screenshot()

im变量将包含一个屏幕快照的Image对象。现在可以调用im变量中Image对象的方法，就像所有其他Image对象一样。在交互式环境中输入以下内容：>>> im.getpixel((0, 0)) (176, 176, 175) >>> im.getpixel((50, 200)) (130, 135, 144)

向getpixel() 函数传入坐标元组，如（0，0）或（50，200），它将告诉你图像中这些坐标处的像素颜色。getpixel() 函数的返回值是一个RGB元组，包含3个整数，表示像素的红绿蓝值（没有第四个值表示alpha，因为屏幕快照是完全不透明的）。这就是你的程序"看到"当前屏幕上内容的方法。

### 18.6.2 分析屏幕快照假设你的GUI自动化程序中，有一步是点击灰色按钮。在调用click() 方法之前，你可以获取屏幕快照，查看脚本要点击处的像素。如果它的颜色和灰色按钮不一样，那么程序就知道出问题了。也许窗口发生了意外的移动，或者弹出式对话框挡住了该按钮。这时，不应该继续（可能会点击到错误的东西，造成严重破坏），程序可以"看到"它没有点击在正确的东西上，并自行停止。

如果屏幕上指定的 x、y 坐标处的像素与指定的颜色匹配，PyAutoGUI 的pixelMatchesColor() 函数将返回True。第一和第二个参数是整数，对应x和y坐标。第三个参数是一个元组，包含3个整数，是屏幕像素必须匹配的RGB颜色。在交互式环境中输入以下内容： >>> import pyautogui >>> im = pyautogui.screenshot() 1. >>> im.getpixel((50, 200)) (130, 135, 144) 2. >>> pyautogui.pixelMatchesColor(50, 200, (130, 135, 144)) True 3. >>> pyautogui.pixelMatchesColor(50, 200, (255, 135, 144)) False

在获取屏幕快照，并用getpixel() 函数取得特定坐标处像素颜色的RGB元组之后1. ，将同样的坐标和RGB元组传递给pixelMatchesColor() 2. ，这应该返回True。然后改变RBG元组中的一个值，用同样的坐标再次调用pixelMatches Color() 3. ，这应该返回False。你的GUI自动化程序要调用click() 之前，这种方法应该有用。请注意，给定坐标处的颜色应该"完全"匹配。即使只是稍有差异（例如，是（255，255，254）而不是（255，255，255）），那么函数也会返回False。

## 18.7 项目：扩展mouseNow程序可以扩展本章前面的mouseNow.py项目，让它不仅给出鼠标当前位置的x、 y坐标，也给出这个像素的RGB颜色。将mouseNow.py中while循环内的代码修改为：#! python3 # mouseNow.py - Displays the mouse cursor's current position. --snip -- positionStr = 'X: ' + str(x).rjust(4) + ' Y: ' + str(y).rjust(4) pixelColor = pyautogui.screenshot().getpixel((x, y))positionStr += ' RGB: (' + str(pixelColor[0]).rjust(3)positionStr += ', ' + str(pixelColor[1]).rjust(3)positionStr += ', ' + str(pixelColor[2]).rjust(3) + ')' print(positionStr, end='') --snip --

现在，如果运行mouseNow.py，那么输出将包括鼠标光标处像素的RGB颜色值。Press Ctrl-C to quit. X: 406 Y: 17 RGB: (161, 50, 50)

这个信息，配合pixelMatchesColor() 函数，应该使得给GUI自动化脚本添加颜色检查变得容易。

## 18.8 图像识别但是，如果事先不知道应该点击哪里，怎么办？可以使用图像识别。向PyAutoGUI提供希望点击的图像，让它去弄清楚坐标。

例如，如果你以前获得了屏幕快照，截取了提交按钮的图像，保存为submit.png，那么 locateOnScreen() 函数将返回图像所在处的坐标。要了解 locateOnScreen()函数的工作方式，请获取屏幕上一小块区域的屏幕快照，保存该图像，并在交互式环境中输入以下内容，用你的屏幕快照文件名代替 'submit. png'：>>> import pyautogui >>> pyautogui.locateOnScreen('submit.png') (643, 745, 70, 29)

locateOnScreen() 函数返回４个整数的元组，是屏幕上首次发现该图像时左边的x坐标、顶边的y坐标、宽度以及高度。如果你用自己的屏幕快照，在你的计算机上尝试，那么返回值会和这里显示的不一样。

如果屏幕上找不到该图像，locateOnScreen() 函数将返回None。请注意要成功识别，屏幕上的图像必须与提供的图像完全匹配。即使只差一个像素，locateOn Screen() 函数也会返回None。

如果该图像在屏幕上能够找到多处，locateAllOnScreen() 函数将返回一个Generator对象。可以将它传递给list() ，返回一个4整数元组的列表。继续在交互式环境的例子中输入以下内容（用你自己的图像文件名取代 'submit.png'）：>>> list(pyautogui.locateAllOnScreen('submit.png')) [(643, 745, 70, 29), (1007, 801, 70, 29)]

每个４整数元组代表了屏幕上的一个区域。如果图像只找到一次，返回的列表就只包含一个元组。

在得到图像所在屏幕区域的4整数元组后，就可以点击这个区域的中心。将元组传递给center() 函数，它将返回该区域中心的x、y坐标。在交互式环境中输入以下内容，用你自己的文件名、4整数元组和坐标对，来取代参数：>>> pyautogui.locateOnScreen('submit.png') (643, 745, 70, 29) >>> pyautogui.center((643, 745, 70, 29)) (678, 759) >>> pyautogui.click((678, 759))

用center() 得到中心坐标后，将click() 坐标传递给函数，就会点击屏幕上该区域的中心，这个区域匹配你传递给locateOnScreen() 函数的图像。

## 18.9 控制键盘

pyautogui也有一些函数向计算机发送虚拟按键，让你能够填充表格，或在应用中输入文本。

### 18.9.1 通过键盘发送一个字符串

pyautogui.typewrite() 函数向计算机发送虚拟按键。这些按键产生什么效果，取决于当前获得焦点的窗口和文本输入框。可能需要先向文本输入框发送一次鼠标点击，确保它获得焦点。

举一个简单的例子，让我们用Python自动化在文件编辑窗口中输入Hello world!。首先，打开一个新的文件编辑窗口，将它放在屏幕的左上角，以便pyautogui点击正确的位置，让它获得焦点。然后，在交互式环境中输入以下内容：>>> pyautogui.click(100, 100); pyautogui.typewrite('Hello world!')

请注意，在同一行中放两条命令，用分号隔开，这让交互式环境不会在两个指令之间提示输入。这防止了你在click() 和typewrite() 调用之间，不小心让新的窗口获得焦点，从而让这个例子失败。

Python首先在坐标（100，100）处发出虚拟鼠标点击，这将点击文件编辑窗口，让它获得焦点。typewrite() 函数调用将向窗口发送文本Hello world!，结果就像图18-3。现在有了替你打字的代码！

图18-3 用PyAutogGUI点击文件编辑器窗口，在其中输入Hello world！

默认情况下，typewrite() 函数将立即打印出完整字符串。但是，你可以传入可选的第二参数，在每个字符之间添加短时间暂停。例如，pyautogui.typewrite（'Helloworld!'，0.25）将在打出H后等待1/4秒。打出e以后再等待1/4秒，如此等等。这种渐进的打字机效果，对于较慢的应用可能有用，它们处理击键的速度不够快，跟不上pyautogui。

对于A或!这样的字符，pyautogui将自动模拟按住Shift键。

### 18.9.2 键名不是所有的键都很容易用单个文本字符来表示。例如，如何把Shift键或左箭头键表示为单个字符？在PyAutoGUI中，这些键表示为短的字符串值：'esc' 表示Esc键，'enter' 表示Enter。

除了单个字符串参数，还可以向typewrite() 函数传递这些键字符串的列表。例如，以下的调用表示按a键，然后是b键，然后是左箭头两次，最后是X和Y键：>>> pyautogui.typewrite(['a', 'b', 'left', 'left', 'X', 'Y'])

因为按下左箭头将移动键盘光标，所以这会输出XYab。表18-1列出了pyautogui的键盘键字符串，你可以将它们传递给typewrite() 函数，模拟任何按键组合。

也可以查看pyautogui.KEYBOARD_KEYS列表，看看pyautogui接受的所有可能的键字符串。'shift' 字符串指的是左边的Shift键，它等价于 'shiftleft'。'ctrl'、'alt' 和 'win' 字符串也一样，它们都是指左边的键。

表18-1 PyKeyboard属性键盘键字符串含义

'a', 'b', 'c', 'A', 'B', 'C', '1', '2', '3', '!', '@', '#'，等等单个字符的键

'enter'（or 'return' or '\n'）

回车键

'esc'

Esc键

'shiftleft', 'shiftright'

左右Shift键

'altleft', 'altright'

左右Alt键

'ctrlleft', 'ctrlright'

左右Ctrl键

'tab'（or '\t'）

Tab键

'backspace', 'delete'

Backspace和Delete键

'pageup', 'pagedown'

Page Up和Page Down键

'home', 'end'

Home和End键

'up', 'down', 'left', 'right'

上下左右箭头键

'f1', 'f2', 'f3'，等等

F1至F12键

'volumemute', 'volumedown', 'volumeup'

静音、减小音量、放大音量键（有些键盘没有这些键，但你的操作系统仍能理解这些模拟的按键）

'pause'

Pause键

'capslock', 'numlock', 'scrolllock'

Caps Lock，Num Lock和Scroll Lock键

'insert'

Ins或Insert键

'printscreen'

Prtsc或Print Screen键

'winleft', 'winright'

左右Win键（在Windows上）

'command'

Command键（在OS X上）

'option'

Option键（在OS X上）

### 18.9.3 按下和释放键盘就像mouseDown() 和mouseUp() 函数一样，pyautogui.keyDown() 和pyautogui. keyUp() 将向计算发送虚拟的按键和释放。它们将根据参数发送键字符串（参见表18-1）。方便起见，pyautogui提供了pyautogui.press() 函数，它调用这两个函数，模拟完整的击键。

运行下面的代码，它将打印出美元字符（通过按住Shift键并按4得到）：>>> pyautogui.keyDown('shift'); pyautogui.press('4'); pyautogui.keyUp('shift')

这行代码按下Shift，按下（并释放）4，然后再释放Shift。如果你需要在文本输入框内打一个字符串，typewrite() 函数就更适合。但对于接受单个按键命令的应用，press() 函数是更简单的方式。

### 18.9.4 热键组合

"热键"或"快捷键"是一种按键组合，它调用某种应用功能。拷贝选择内容的常用热键是Ctrl-C（在Windows和Linux上）或⌘-C（在OS X上）。用户按住Ctrl键，然后按C键，然后释放C和Ctrl键。要用pyautogui的keyDown() 和keyUp() 函数来做到这一点，必须输入以下代码：pyautogui.keyDown('ctrl') pyautogui.keyDown('c') pyautogui.keyUp('c') pyautogui.keyUp('ctrl')

这相当复杂。作为替代，可以使用pyautogui.hotkey() 函数，它接受多个键字符串参数，按顺序按下，再按相反的顺序释放。例如对于Ctrl-C，代码就像下面这样简单：pyautogui.hotkey('ctrl', 'c')

对于更大的热键组合，这个函数特别有用。在Word中，Ctrl-Alt-Shift-S热键组合显示Style（样式）窗口。不必使用8次不同的函数调用（4次keyDown() 调用和4次keyUp() 调用），你只要调用hotkey（'ctrl', 'alt', 'shift', 's'）。

在屏幕的左上角打开一个新的IDLE文件编辑窗口，在交互式环境中输入以下内容（在OS X中，用 'ctrl' 代替 'alt'）： >>> import pyautogui, time >>> def commentAfterDelay(): 1. pyautogui.click(100, 100) 2. pyautogui.typewrite('In IDLE, Alt-3 comments out a line.')time.sleep(2) 3. pyautogui.hotkey('alt', '3') >>> commentAfterDelay()

这定义了一个函数commentAfterDelay()，在被调用时，将点击文件编辑窗口，让它获得焦点1. ，输出"In IDLE，Alt-3 comments out a line"2. ，暂停２秒钟，然后模拟按下Alt-3热键（或OS X上的ctrl-3）3. 。这个快捷键在当前行加上两个#字符，将它注释掉（在IDLE中编写你自己的代码时，这是一个有用的技巧，应该知道）。

## 18.10 复习PyAutoGUI的函数本章介绍了许多不同函数，下面是快速的汇总参考：

moveTo（x，y）将鼠标移动到指定的x、y坐标。

moveRel（xOffset，yOffset）相对于当前位置移动鼠标。

dragTo（x，y）按下左键移动鼠标。

dragRel（xOffset，yOffset）按下左键，相对于当前位置移动鼠标。

click（x，y，button）模拟点击（默认是左键）。

rightClick() 模拟右键点击。

middleClick() 模拟中键点击。

doubleClick() 模拟左键双击。

mouseDown（x，y，button）模拟在x、y处按下指定鼠标按键。

mouseUp（x，y，button）模拟在x、y处释放指定键。

scroll（units）模拟滚动滚轮。正参数表示向上滚动，负参数表示向下滚动。

typewrite（message）键入给定消息字符串中的字符。

typewrite（[key1，key2，key3]）键入给定键字符串。

press（key）按下并释放给定键。

keyDown（key）模拟按下给定键。

keyUp（key）模拟释放给定键。

hotkey（[key1，key2，key3]）模拟按顺序按下给定键字符串，然后以相反的顺序释放。

screenshot() 返回屏幕快照的Image对象（参见第17章关于Image对象的信息）。

## 18.11 项目：自动填表程序在所有无聊的任务中，填表是最烦人的。到了现在，在最后一章的项目中，你将搞定它。假设你在电子表格中有大量的数据，必须重复将它输入到另一个应用的表单界面中，没有实习生帮你完成。尽管有些应用有导入功能，让你上传包含信息的电子表格，但有时候似乎没有其他方法，只好不动脑子地点击和输入几个小时。读到了本书的这一章，你"当然"知道会有其他方法。

本项目的表单是 Google Docs 表单，你可以在 http://nostarch.com/automatestuff 找到，如图18-4所示。

图18-4 本项目用到的表单总的来说，你的程序应该做到：

- 点击表单的第一个文本字段。

- 遍历表单，在每个输入栏键入信息。

- 点击Submit按钮。

- 用下一组数据重复这个过程。

这意味着代码需要做下列事情：

- 调用pyautogui.click() 函数，点击表单和Submit按钮。

- 调用pyautogui.typewrite() 函数，在输入栏输入文本。

- 处理KeyboardInterrupt异常，这样用户能按Ctrl-C键退出。

打开一个新的文件编辑器窗口，将它保存为formFiller.py。

### 第1步：弄清楚步骤在编写代码之前，你需要弄清楚填写一次表格时，需要的准确击键和鼠标点击。18.4节中的mouseNow.py脚本可以帮助你弄清楚确切的鼠标坐标。你只需要知道第一个文本输入栏的坐标。在点击第一个输入栏之后，你可以Tab键，将焦点移到下一个输入栏。这让你不必弄清楚每一个输入栏的x、y坐标。

下面是在表单中输入数据的步骤：

1．点击Name输入栏（在将浏览器窗口最大化后，用mouseNow.py程序来确定坐标。在OS X上，可能需要点击两次：一次让浏览器获得焦点，第二次让Name输入栏获得焦点）。

2．键入名称，然后按Tab键。

3．键入最大的恐惧（greatest fear），然后按Tab键。

4．按向下键适当的次数，选择魔力源（wizard power source）：一次是Wand，两次是Amulet，三次是Crystal ball，四次是money。然后按Tab键（请注意，在OS X中，你必须为每次选择多按一次向下键。对于某些浏览器，你也需要按回车键）。

5．按向右键，选择RoboCop问题的答案。按一次是2，两次是3，三次是4，四次是5，或按空格键选择1（它是默认加亮的）。然后按Tab键。

6．键入附加的备注，然后按Tab键。

7．按回车键，点击"Submit"按钮。

8．在提交表单后，浏览器将转到一个页面。然后你需要点击一个链接，返回到表单页面。

请注意，如果你稍后再次运行这个程序，可能需要更新鼠标点击的坐标，因为浏览器窗口可能已经改变了位置。要避免这一点，请一直确保浏览器窗口最大化，然后再寻找第一个表单输入框的坐标。而且，不同操作系统上的不同浏览器，工作起来可能与这里的步骤稍有不同，所以在运行程序之前，要确保这些击键组合适合你的计算机。

### 第2步：建立坐标在浏览器中载入示例表单（图18-4），并将浏览器窗口最大化。打开一个新的终端窗口或命令行窗口，来运行mouseNow.py脚本，然后将鼠标放在输入框上，弄清楚它的x、y坐标。这些数字将赋给程序中的变量。同时，找出蓝色Submit按钮的x、y坐标和RBG值。这些值将分别赋给变量submitButton和submitButtonColor。

接下来，在表单中填入一些假的数据，点击Submit。你需要看到下一个页面的样子，以便使用程序mouseNow.py寻找这个页面中Submit another response链接的坐标。

让你的源代码看起来像下面的样子。确保用自己测试得到的坐标代替斜体的值： #! python3 # formFiller.py - Automatically fills in the form. import pyautogui, time # Set these to the correct coordinates for your computer. nameField = (648 , 319 ) submitButton = (651 , 817 ) submitButtonColor = (75 , 141 , 249 ) submitAnotherLink = (760 , 224 ) # TODO: Give the user a chance to kill the script. # TODO: Wait until the form page has loaded. # TODO: Fill out the Name Field. # TODO: Fill out the Greatest Fear(s) field. # TODO: Fill out the Source of Wizard Powers field. # TODO: Fill out the RoboCop field. # TODO: Fill out the Additional Comments field. # TODO: Click Submit. # TODO: Wait until form page has loaded. # TODO: Click the Submit another response link.

现在你需要实际想要输入这张表格的数据。在真实世界中，这些数据可能来自电子表格、纯文本文件或某个网站。可能需要额外的代码，将数据加载到程序中。但对于这个项目，只需要将这些数据硬编码给一个变量。在程序中加入以下代码：

#! python3 # formFiller.py - Automatically fills in the form. --snip -- formData = [{'name': 'Alice', 'fear': 'eavesdroppers', 'source': 'wand','robocop': 4, 'comments': 'Tell Bob I said hi.'},{'name': 'Bob', 'fear': 'bees', 'source': 'amulet', 'robocop': 4,'comments': 'n/a'},{'name': 'Carol', 'fear': 'puppets', 'source': 'crystal ball','robocop': 1, 'comments': 'Please take the puppets out of thebreak room.'},{'name': 'Alex Murphy', 'fear': 'ED-209', 'source': 'money','robocop': 5, 'comments': 'Protect the innocent. Serve the publictrust. Uphold the law.'},] --snip --

formData列表包含4个字典，针对4个不同的名字。每个字典都有文本字段的名字作为键，响应作为值。最后一点准备是设置pyautogui的PAUSE变量，在每次函数调用后等待半秒钟。在程序的formData赋值语句后，添加下面的代码：

pyautogui.PAUSE = 0.5

### 第3步：开始键入数据

for循环将迭代formData列表中的每个字典，将字典中的值传递给pyautogui函数，最后在文本输入区输入。

在程序中添加以下代码： #! python3 # formFiller.py - Automatically fills in the form. --snip -- for person in formData:# Give the user a chance to kill the script.print('>>> 5 SECOND PAUSE TO LET USER PRESS CTRL-C <<<') 1. time.sleep(5)# Wait until the form page has loaded. 2. while not pyautogui.pixelMatchesColor(submitButton[0], submitButton[1],submitButtonColor):time.sleep(0.5) --snip --

作为一个小的安全功能，该脚本有 5 秒暂停1. 。如果发现程序在做一些预期之外的事，这让用户有机会按 Ctrl-C（或将鼠标移到屏幕的左上角，触发FailSafeException异常），从而关闭程序。然后程序等待，直到Submit按钮的颜色可见2. ，这让程序知道，表单页面已经加载了。回忆一下，你在第2步中已经弄清楚了坐标和颜色信息，并将它们保存在submitButton和submitButtonColor变量中。要调用pixelMatchesColor()，就传递坐标submitButton[0] 和submitButton[1]，以及颜色submitButtonColor。

在等待Submit按钮颜色可见的代码之后，添加以下代码： #! python3 # formFiller.py - Automatically fills in the form. - -snip -- 1. print('Entering %s info...' % (person['name'])) 2. pyautogui.click(nameField[0], nameField[1])# Fill out the Name field. 3. pyautogui.typewrite(person['name'] + '\t')# Fill out the Greatest Fear(s) field. 4. pyautogui.typewrite(person['fear'] + '\t') --snip --

我们添加了偶尔的print() 调用，在终端窗口中显示程序的状态，让用户知道进展。1.

既然程序知道表格已经加载，就可以调用click()，点击Name输入框2. ，并调用typewrite()，输入person['name'] 中的字符串3. 。字符串末尾加上了 '\t' 字符，模拟按下Tab键，它将输入焦点转向下一个输入框，Greatest Fear（s）。另一次typewrite() 调用，将在这个输入框中输入person['fear'] 中的字符串，然后用Tab跳到表格的下一个输入框4. 。

### 第4步：处理选择列表和单选按钮

"wizard powers"问题的下拉菜单和RoboCop字段的单选按钮，处理起来比文本输入框需要更多技巧。要用鼠标点选这些选项，你必须搞清楚每个可能选项的x、y坐标。然而，用箭头键来选择会比较容易。

在程序中加入以下代码： #! python3 # formFiller.py - Automatically fills in the form. --snip -- # Fill out the Source of Wizard Powers field. 1. if person['source'] == 'wand': 2. pyautogui.typewrite(['down', '\t'])elif person['source'] == 'amulet':pyautogui.typewrite(['down', 'down', '\t'])elif person['source'] == 'crystal ball':pyautogui.typewrite(['down', 'down', 'down', '\t'])elif person['source'] == 'money':pyautogui.typewrite(['down', 'down', 'down', 'down', '\t'])# Fill out the RoboCop field. 3. if person['robocop'] == 1: 4. pyautogui.typewrite([' ', '\t'])elif person['robocop'] == 2:pyautogui.typewrite(['right', '\t'])elif person['robocop'] == 3:pyautogui.typewrite(['right', 'right', '\t'])elif person['robocop'] == 4:pyautogui.typewrite(['right', 'right', 'right', '\t'])elif person['robocop'] == 5:pyautogui.typewrite(['right', 'right', 'right', 'right', '\t']) --snip --

在下拉菜单获得焦点后（回忆一下，你写了代码，在填充Greatest Fear（s）输入框后模拟了按 Tab 键），按下向下箭头，就会移动到选择列表的下一项。根据person['source'] 中的值，你的程序应该发出几次向下按键，然后再切换到下一个输入区。如果这个用户词典中的 'source' 值是 'wand' 1. ，我们模拟按向下键一次（选择Wand），并按Tab键2. 。如果 'source' 键的值是 'amulet'，模拟按向下键两次，并按Tab键。对其他可能的值也是类似。

RoboCop问题的单选按钮，可以用向右键来选择。或者，如果你想选择第一个选项3. ，就按空格键4. 。

### 第5步：提交表单并等待可以用函数typewrite() 填写备注输入框，将person['comments'] 作为参数。你可以另外输入 '\t'，将焦点移到下一个输入框或Submit按钮。当Submit按钮获得焦点后，调用pyautogui.press（'enter'），模拟按下回车键，提交表单。在提交表单之后，程序将等待5秒，等下一页加载。

在新页面加载之后，它会有一个Submit another response链接，让浏览器转向一个新的、全空的表单页面。在第二步，你已将这个链接的坐标作为元组保存在submitAnotherLink中，所以将这些坐标传递给pyautogui.click()，点击这个链接。

新的表单准备好后，脚本的外层for循环将继续下一次迭代，在表单中输入下一个人的信息。

添加以下代码，完成你的程序：

#! python3 # formFiller.py - Automatically fills in the form. --snip -- # Fill out the Additional Comments field.pyautogui.typewrite(person['comments'] + '\t')# Click Submit.pyautogui.press('enter')# Wait until form page has loaded.print('Clicked Submit.')time.sleep(5)# Click the Submit another response link.pyautogui.click(submitAnotherLink[0], submitAnotherLink[1])

在主for循环完成后，程序应该已经插入了每个人的信息。在这个例子中，只有4个人要输入。但如果有4000个人，那么编程来完成这个任务将节省大量的输入时间。

## 18.12 小结用pyautogui模块实现GUI自动化，通过控制键盘和鼠标，让你与计算机上的应用程序交互。虽然这种方式相当灵活，可以做任何人类用户做的事情，但也有不足之处，即这些程序对它们的点击和键入是相当盲目的。在编写GUI自动化程序时，请试着确保它们在得到错误指令时快速崩溃。崩溃很烦人，但比程序继续错误要好得多。

利用pyautogui，你可以在屏幕上移动鼠标，模拟鼠标点击、击键和快捷键。pyautogui模块也能检查屏幕上的颜色，让GUI自动化程序对屏幕内容有足够的了解，知道它是否有偏差。甚至可以向它提供一个屏幕快照，让它找出你希望点击的区域坐标。

可以组合使用所有这些pyautogui功能，在计算机上自动化各种无脑的重复任务。实际上，看着鼠标自己移动，看着文本自动出现在屏幕上，这是彻头彻尾的催眠。为什么不用节省下来的时间，舒舒服服地坐着，看着程序为你工作？看着你的聪明才智帮你省去无聊的工作，肯定会让你感到满意。

## 18.13 习题

1．如何触发pyautogui的失效保护来停止程序？

2．什么函数返回当前的分辨率？

3．什么函数返回鼠标当前位置的坐标？

4．pyautogui.moveTo() 和pyautogui.moveRel() 函数之间的区别是什么？

5．什么函数用于拖放鼠标？

6．调用什么函数将替你键入字符串"Hello world!"？

7．如何模拟按下向左键这样的特殊键？

8．如何将当前屏幕的内容保存为图形文件并命名为screenshot.png？

9．什么代码能够设置每次pyautogui函数调用后暂停两秒钟？

## 18.14 实践项目作为实践，编程完成下面的内容。

### 18.14.1 看起来很忙许多即时通信程序通过一段时间鼠标不动（例如10分钟），来判断你空闲或离开了计算机。也许你想从桌子边溜走一段时间，但不想让别人看到你的即时通信软件转为空闲状态。请编写一段脚本，每隔10秒钟稍微动一下鼠标。这种移动应该相当小，以便在脚本运行时，如果你需要使用计算机，它也不会给你制造麻烦。

### 18.14.2 即时通信机器人

Google Talk、Skype、Yahoo Messenger、AIM和其它即时通信应用通常使用专有协议，让其他人很难通过编写Python模块与这些程序交互。但即使这些专有协议，也不能阻止你编写GUI自动化工具。

Google Talk应用有一个搜索条，让你在输入朋友列表中的用户名并按下回车时，打开一个消息窗口。键盘焦点自动移到那个新的窗口。其他即时通信应用也有类似的方式，来打开新的消息窗口。请编写一个应用程序，向朋友列表中选定的一组人发出一条通知消息。程序应该能够处理异常情况，比如朋友离线，聊天窗口出现在屏幕上不同的位置，或确认对话框打断输入消息。程序必须使用屏幕快照，指导它的GUI交互，并在虚拟按键发送之前采用各种检测方式。

注意你可能需要建立一些假的测试账户，这样就不会在编写这个程序时，不小心打扰真正的朋友。

### 18.14.3 玩游戏机器人指南有一个很不错的指南名为"How to Build a Python Bot That Can Play Web Games"，网址是http://nostarch.com/automatestuff/。这份指南解释了如何用Python创建一个GUI自动化程序，玩一个名为Sushi Go Round的Flash游戏。这个游戏需要点击正确的成分按钮，填写客户的寿司订单。填写无错订单越快，得分就越高。这个任务特别适合GUI自动化程序，因为可以作弊得到高分！这份指南包含了本章介绍的许多主题，也涉及PyAutoGUI的基本图像识别功能。

# 附录A 安装第三方模块除了Python自带的标准库，其他开发者写了一些自己的模块，进一步扩展了Python的功能。安装第三方模块的主要方法是使用Python的pip工具。这个工具从Python软件基金会的网站https://pypi.python.org/ 安全地下载Python模块，并安装到您的计算机上。PyPI或Python包索引，就像是Python模块的免费应用程序商店。

## A.1 pip工具

pip工具的可执行文件在Windows上称为pip，在OS X和Linux上称为pip3。在Windows上，pip位于C:\Python34\Scripts\pip.exe。在OS X上，它位于/Library/ Frameworks/Python.framework/Versions/3.4/bin/pip3。在Linux上，它位于/usr/bin/pip3。

虽然在Windows和OS X上pip会随Python3.4自动安装，但在Linux上，必须单独安装。要在Ubuntu或Debian Linux上安装pip3，就打开一个新的终端窗口，输入get install python3-pip。要在Fedora Linux上安装pip3，就在终端窗口输入install python3 -pip。为了安装这个软件，需要输入计算机的管理员密码。

## A.2 安装第三方模块

pip工具需要在命令行中运行：向它传入install命令，跟上想要安装的模块名称。例如，在Windows上，会输入pip install ModuleName，其中ModuleName是模块的名称。在OS X和Linux，必须加sudo前缀来运行pip3，授予管理权限来安装该模块。需要输入sudo pip3 install ModuleName。

如果你已经安装了模块，但想升级到PyPI上提供的最新版本，就运行pip install -U ModuleName（或在OS X和Linux上运行pip3 install -U ModuleName）。

安装模块后，可以在交互式环境中运行import ModuleName，测试安装是否成功。如果未显示错误信息，就可以认为该模块已经成功安装。

运行下面列出的命令，你可以安装本书中介绍的所有模块（请记住，如果在OS X或Linux上，用pip3替代pip）。

- pip install send2trash- pip install requests- pip install beautifulsoup4- pip install selenium- pip install openpyxl- pip install PyPDF2- pip install python-docx（安装python-docx，而不是docx）- pip install imapclient- pip install pyzmail- pip install twilio- pip install pillow- pip install pyobjc-core（仅在OS X上）- pip install pyobjc（仅在OS X上）- pip install python3-xlib（仅在Linux上）- pip install pyautogui

注意对于OS X用户：pyobjc模块需要20分钟或更长的时间来安装，因此，如果它需要一段时间，不要惊慌。也应该先安装pyobjc核心模块，这将减少整体安装时间。

# 附录B 运行程序如果你在IDLE的文件编辑器中打开了一个程序，运行它很简单，按F5或选择Run►Run Module菜单项。这是在编程时运行程序的最简单方法，但打开IDLE来运行已完成的程序可能有点累。执行Python脚本还有更方便的方法。

## B.1 第一行所有Python程序的第一行应该是#!行，它告诉计算机你想让Python来执行这个程序。该行以#!开始，但剩下的内容取决于操作系统。

- 在Windows上，第一行是 #! python3。

- 在OS X，第一行是 #! /usr/bin/env python3。

- 在Linux上，第一行是 #! /usr/bin/python3。

没有#!行，你也能从IDLE运行Python脚本，但从命令行运行它们就需要这一行。

## B.2 在Windows上运行Python程序在Windows上，Python3.4的解释程序位于C:\Python34\python.exe。或者，方便的py.exe程序将读取.py文件源代码顶部的#!行，并针对该脚本运行相应的Python版本。如果计算机上安装了多个版本的Python，py.exe程序确保运行正确版本的Python程序。

为了方便运行你的Python程序，可以创建一个.BAT批处理文件，用py.exe来运行Python程序。要创建一个批处理文件，就创建一个新的文本文件，包含一行内容，类似下面这样：@py.exe C:\path\to\your\pythonScript.py %*

用你自己的程序的绝对路径替换该路径，将这个文件以.bat 文件扩展名保存（例如，pythonScript.bat）。这个处理文件将使你不必在每次运行时，都输入Python程序完整的绝对路径。我建议将所有的批处理文件和.py 文件放在一个文件夹中，如C:\MyPythonScripts或C:\Users\YourName\PythonScripts。

在Windows上，C:\MyPythonScripts文件夹应该添加到系统路径中，这样就可以从Run对话框中运行其中的批处理文件。要做到这一点，请修改PATH环境变量。单击"开始"按钮，并输入"Edit environment variables for your account（编辑账户的环境变量）"。在你开始输入时，该选项应自动完成。弹出的环境变量窗口如图B-1所示。

图B-1 Windows的环境变量窗口从系统变量中，选择Path变量，然后单击"编辑"。在"变量值"文本字段中，追加一个分号，键入C:\MyPythonScripts，然后单击"确定"。现在你只需按下Win-R并输入脚本的名称，就能运行C:\MyPythonScripts文件夹中的Python脚本。例如，运行pythonScript，将运行pythonScript.bat，这使你不必从Run对话框运行整个命令py.exe C:\MyPythonScripts\pythonScript.py。

## B.3 在OS X和Linux上运行Python程序在OS X上，选择Applications►Utilities►Terminal将弹出一个终端窗口。终端窗口让你用纯文本在计算机上输入命令，而不是通过图形界面点击。要在Ubuntu Linux上打开终端窗口，就按Win（或Super）键，调出Dash并输入Terminal。

终端窗口将从你的用户账户的主文件夹开始。如果我的用户名是sweigart，OS X上主文件夹在/Users/asweigart，Linux上在/home/asweigart。波浪纯字符（~）是主文件夹的快捷方式，所以你可以输入cd ~切换到主文件夹。也可以使用cd命令，将当前工作目录改变到任何其他目录。在OS X和Linux上，pwd命令将打印当前工作目录。

为了运行Python程序，将你的.py文件保存到你的主文件夹。然后，更改.py文件的权限，运行chmod +x pythonScript.py，使之成为可执行文件。文件权限超出了本书的范围，但如果你想在终端窗口运行程序，就需要对Python文件运行此命令。这样做之后，当你打开一个终端窗口，输入./pythonScript.py，就能运行该脚本。脚本顶部的#!行会告诉操作系统，在哪里可以找到Python解释器。

# 欢迎来到异步社区！

## 异步社区的来历异步社区(www.epubit.com.cn )是人民邮电出版社旗下IT专业图书旗舰社区，于2015年8月上线运营。

异步社区依托于人民邮电出版社20余年的IT专业优质出版资源和编辑策划团队，打造传统出版与电子出版和自出版结合、纸质书与电子书结合、传统印刷与POD按需印刷结合的出版平台，提供最新技术资讯，为作者和读者打造交流互动的平台。

## 社区里都有什么？

### 购买图书我们出版的图书涵盖主流IT技术，在编程语言、Web技术、数据科学等领域有众多经典畅销图书。社区现已上线图书1000余种，电子书400多种，部分新书实现纸书、电子书同步出版。我们还会定期发布新书书讯。

### 下载资源社区内提供随书附赠的资源，如书中的案例或程序源代码。

另外，社区还提供了大量的免费电子书，只要注册成为社区用户就可以免费下载。

### 与作译者互动很多图书的作译者已经入驻社区，您可以关注他们，咨询技术问题；可以阅读不断更新的技术文章，听作译者和编辑畅聊好书背后有趣的故事；还可以参与社区的作者访谈栏目，向您关注的作者提出采访题目。

## 灵活优惠的购书您可以方便地下单购买纸质图书或电子图书，纸质图书直接从人民邮电出版社书库发货，电子书提供多种阅读格式。

对于重磅新书，社区提供预售和新书首发服务，用户可以第一时间买到心仪的新书。

用户帐户中的积分可以用于购书优惠。100积分=1元，购买图书时，在里填入可使用的积分数值，即可扣减相应金额。

特别优惠购买本电子书的读者专享异步社区优惠券 。 使用方法：注册成为社区用户，在下单购书时输入"57AWG "，然后点击"使用优惠码"，即可享受电子书8折优惠（本优惠券只可使用一次）。

### 纸电图书组合购买社区独家提供纸质图书和电子书组合购买方式，价格优惠，一次购买，多种阅读选择。

## 社区里还可以做什么？

### 提交勘误您可以在图书页面下方提交勘误，每条勘误被确认后可以获得100积分。热心勘误的读者还有机会参与书稿的审校和翻译工作。

### 写作社区提供基于Markdown的写作环境，喜欢写作的您可以在此一试身手，在社区里分享您的技术心得和读书体会，更可以体验自出版的乐趣，轻松实现出版的梦想。

如果成为社区认证作译者，还可以享受异步社区提供的作者专享特色服务。

### 会议活动早知道您可以掌握IT圈的技术会议资讯，更有机会免费获赠大会门票。

## 加入异步扫描任意二维码都能找到我们：

异步社区微信订阅号微信服务号官方微博

QQ群：368449889

社区网址：www.epubit.com.cn

官方微信： 异步社区官方微博： @人邮异步社区，@人民邮电出版社-信息技术分社投稿&咨询： contact@epubit.com.cn

# 版权信息书名：Python极客项目编程

ISBN：978-7-115-44976-4

本书由人民邮电出版社发行数字版。版权所有，侵权必究。

您购买的人民邮电出版社电子书仅供您个人使用，未经授权，不得以任何方式复制和传播本书内容。

我们愿意相信读者具有这样的良知和觉悟，与我们共同保护知识产权。

如果购买者有侵权行为，我们可能对该用户实施包括但不限于关闭该帐号等维权措施，并可能追究法律责任。

- 著 [美] Mahesh Venkitachalam

译王海鹏责任编辑陈冀康

- 人民邮电出版社出版发行北京市丰台区成寿寺路11号邮编 100164 电子邮件 315@ptpress.com.cn

网址 http://www.ptpress.com.cn

- 读者服务热线：(010)81055410

反盗版热线：(010)81055315

# 版权声明

Simplified Chinese-language edition copyright © 2017 by Posts and Telecom Press.

Copyright © 2016 by Mahesh Venkitachalam. Title of English-language original: Python Playground ，ISBN-13: 978-1-59327-604-1，published by No Starch Press.

All rights reserved.

本书中文简体字版由美国No Starch出版社授权人民邮电出版社出版。未经出版者书面许可，对本书任何部分不得以任何方式复制或抄袭。

版权所有，侵权必究。

# 内容提要

Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。通过Python编程，我们能够解决现实生活中的很多任务。

本书通过14个有趣的项目，帮助和鼓励读者探索Python编程的世界。全书共14章，分别介绍了通过Python编程实现的一些有趣项目，包括解析iTunes播放列表、模拟人工生命、创建ASCII码艺术图、照片拼接、生成三维立体图、创建粒子模拟的烟花喷泉效果、实现立体光线投射算法，以及用Python结合Arduino和树莓派等硬件的电子项目。本书并不介绍Python语言的基础知识，而是通过一系列不简单的项目，展示如何用Python来解决各种实际问题，以及如何使用一些流行的Python库。

本书适合那些想要通过Python编程来进行尝试和探索的读者，适合了解基本的Python语法和基本的编程概念的读者进一步学习，对于Python程序员有一定的启发和参考价值。

# 致谢写一本书就像跑马拉松。有人这么对我说过。但我确实知道，写这本书考验了我的耐力极限，没有亲朋好友和家人为我摇旗呐喊，我不可能完成。

首先，我感谢我的妻子Hema，她不变的爱、鼓励和耐心，贯穿了完成这项工作的整整两年时间。我感谢我的朋友Raviprakash Jayaraman，他是我所有不确定的项目的"同谋"，也是本书的技术评审，我们一起吃了许多有趣的午餐、看了不少电影，多次去逛S.P. Road Zoo。我感谢我的朋友Seby Kallarakkal，他推动我编写这本书，进行了多次有趣的讨论。我很感谢我的朋友Santosh Hemachandra博士在快速傅里叶变换上的有益讨论。我感谢Karthikeyan Chellappa，帮助我测试Python模块的安装，和我一起围绕Kaikondrahalli湖跑步。我还要感谢Matthew Denham（我与他在Reddit上交谈），他对万花尺（Spirograph）的数学知识提供了帮助。

我感谢No Starch出版社的Tyler Ortman和Bill Pollock，他们接受了我编写本书的意向。还要感谢Serena Yang编辑本书的专业工作。我感谢Nicholas Kramer对本书的技术评阅。 我感谢我的父母A.V. Venkitachalam和N. Saraswathy，他们为我提供的教育远远超越了他们的财务能力。最后，我感谢所有给我启发的老师，我希望一辈子做一名学生。

# 前言欢迎阅读本书！在本书中，你会看到14个令人兴奋的项目，旨在鼓励你探索Python编程的世界。这些项目涉及广泛的主题，如绘制类似万花尺的花纹、生成ASCII码艺术图、3D渲染，以及根据音乐同步投射激光图像。除了本身很有趣之外，这些项目的意图是提供一些起点，让你通过扩展每个项目，来探索你自己的想法。

## 本书的目标读者本书的目标读者，是所有想知道如何利用编程来理解和探索想法的人。本书的项目假设你了解基本的Python语法和基本的编程概念，并假设你熟悉高中数学知识。我已经尽了最大的努力，详细解释了所有项目中需要的数学知识。

本书不会是你的第一本Python书。我不会指导你学习基本知识。但我会通过一系列不简单的项目，向你展示如何用Python来解决各种实际问题。在学习这些项目时，你将探索Python编程语言的细微差别，并学习如何使用一些流行的Python库。但也许更重要的是，你将学习如何将问题分解成几个部分，开发一个算法来解决这个问题，然后从头用Python来实现一个解决方案。解决现实世界的问题可能很难，因为它们往往是开放式的，并且需要各个领域的专业知识。但Python提供了一些工具，协助解决问题。克服困难，寻找实际问题的解决方案，这是成为专家级程序员的旅途中最重要的环节。

## 本书的内容让我们快速浏览一下本书各章的内容。

### 第一部分：热身运动第1章展示了如何解析iTunes播放列表文件，并从中收集有用的信息，如音轨长度和共同的音轨。在第2章中，我们使用参数方程及海龟作图法，绘制类似万花尺产生的那些曲线。

### 第二部分：模拟生命这部分是用数学模型来模拟现象。在第3章中，我们将学习如何实现Conway游戏的生命游戏算法，产生动态的模式来创建其他模式，以模拟一种人工生命。第4章展示了如何用Karplus-Strong算法来创建逼真的弹拨音。然后，在第5章中，我们将学习如何实现类鸟群算法，模拟鸟类的聚集行为。

### 第三部分：图像之乐这部分介绍使用Python读取和操作2D图像。第6章展示了如何根据图像创建ASCII码艺术图。在第7章中，我们将进行照片拼接。在第8章中，我们将学习如何生成三维立体图，它让人产生3D图像的错觉。

### 第四部分：走进三维这一部分的项目使用OpenGL的3D图形库。第9章介绍使用OpenGL创建简单3D图形的基本知识。在第10章中，我们将创建粒子模拟的烟花喷泉，它用数学和OpenGL着色器来计算和渲染。在第11章中，我们将使用OpenGL着色器来实现立体光线投射算法，来渲染立体数据，该技术常用于医疗影像，如MRI和CT扫描。

### 第五部分：玩转硬件在最后一部分中，我们将用Python来探索Arduino微控制器和树莓派。在第12章中，我们将利用Arduino，通过一个简单电路读取并标绘传感器数据。在第13章中，我们将利用Python和Arduino来控制两个旋转镜和激光器，生成响应声音的激光秀。在第14章中，我们将使用树莓派打造一个基于网络的气象监测系统。

## 为何选择Python

Python是探索编程的理想语言。作为一种多范式语言，在如何组织程序方面，它提供了极大的灵活性。你可以将Python视为脚本语言，简单地执行代码，或将其视为过程语言，把程序组织成一组彼此调用的函数，或将其视为面向对象语言，利用类、继承和模块来建立层次结构。这种灵活性让你可以选择最适合特定项目的编程风格。

如果用更传统的语言来开发，如C或C ++，你必须先编译和链接代码，然后才能运行它。使用Python，你可以编辑后直接运行它（在背后，Python将你的代码编译成中间字节码，然后由Python解释器运行，但这些过程对用户是透明的）。在实践中，用Python多次修改并运行代码，要容易很多。

此外，Python解释器是非常方便的工具，可用于检查代码语法，获得模块的帮助，进行快速计算，甚至测试在开发中的代码。例如，我写Python代码时，会打开三个窗口：文本编辑器、命令行和Python解释器。我在编辑器中写代码时，会在解释器中导入我的函数或类，边开发边测试。

Python有一组非常小、简单而强大的数据结构。如果你理解了字符串、列表、元组、字典、列表解析和基本控制结构，如for和while循环，那么你已经开了个好头。 Python简洁而有表现力的语法，使得我们很容易只用几行代码，就完成复杂的操作。而一旦熟悉Python内置的模块和第三方模块，你将拥有大量的工具，用于解决真正的问题，就像本书中介绍的那样。从Python中调用C/C++代码有标准的方式，反之亦然。因为在Python中可以找到库来做几乎所有事情，我们很容易在大型项目中组合使用Python和其他语言模块。这就是为什么Python被认为是了不起的胶水语言，它可以很容易地组合使用不同的软件组件。本书最后的硬件项目展示了Python如何与Arduino和JavaScript代码协作。真实的软件项目经常使用多种软件技术，Python非常适合这种分层体系结构。

下面的例子展示了Python的易用性。在第14章中为树莓派天气监控器开发代码时，我看着温度/湿度传感器的示波器输出，写下这一串数字：0011011100000000000110100000000001010001

因为我不能用二进制讲话，所以启动了Python解释器并输入：>>> str = '0011011100000000000110100000000001010001' >>> len(str) 40 >>> [int(str[i:i+8], 2) for i in range(0, 40, 8)] [55, 0, 26, 0, 81]

这行代码将40位字符串切分转换成5个8位的整数，这是我可以理解的。上述数据被解释为55.0%的湿度，温度为26.0摄氏度，校验和是55 + 26 = 81。

这个例子展示了如何实际使用Python解释器作为非常强大的计算器。你不必写一个完整的程序就能快速计算，只要打开解释器，就可以开始。这只是我喜欢Python的一个原因，原因还有很多，所以我认为你也会喜欢Python。

### Python的版本本书基于Python 3.3.3，但所有代码都与Python 2.7.x和3.x兼容。

### 本书的代码在本书中，我尽了最大的努力引导你详细研究每个项目的代码，一段接一段地进行。你可以自己输入代码，或从https://github.com/electronut/pp/ 或www.epubit. com.cn下载书中所有程序的完整源代码（单击Download Zip选项）。

接下来，你会看到一些令人兴奋的项目。我希望你玩这些项目时，享受的乐趣和我创造它们时一样多。而且不要忘记，利用每个项目结束时提供的练习进一步探索。我希望你和本书一起度过许多快乐的编程时光！

# 第一部分热身运动

"在初学者的头脑中有很多可能性，

在专家的头脑中，可能性很少。"

--铃木俊隆

# 第1章解析iTunes播放列表我们的Python探险始于一个简单的项目，该项目在iTunes播放列表文件中查找重复的乐曲音轨，并绘制各种统计数据，如音轨长度和评分。你可以从查看iTunes播放列表格式开始，然后学习如何用Python提取这些文件的信息。为了绘制这些数据，要用到matplotlib库。

在这个项目中，我们将学习以下主题：

- XML和属性列表（p-list）文件；

- Python列表和字典；

- 使用Python的set对象；

- 使用numpy数组；

- 直方图和散点图；

- 用matplotlib库绘制简单的图；

- 创建和保存数据文件。

## 1.1 iTunes播放列表文件剖析

iTunes资料库中的信息可以导出为播放列表文件（在iTunes中选择File►Library►Export Playlist）。播放列表文件以可扩展标记语言（XML）写成，这是一种基于文本的语言，旨在分层表示基于文本的信息。它包括一些用户定义的标签所构成的树状集合，标签形如<MyTag>，每个标签可以有一些属性和子标签，其中包含附加的信息。

如果在文本编辑器中打开一个播放列表文件，你会看到类似这样的简化版本： <?xml version="1.0" encoding="UTF-8"?> 1. <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www apple.com/DTDs/PropertyList-1.0.dtd"> 2. <plist version="1.0"> 3. <dict> 4. <key>Major Version</key><integer>1</integer> <key>Minor Version</key><integer>1</integer> --snip -- 5. <key>Tracks</key> <dict> <key>2438</key> <dict> <key>Track ID</key><integer>2438</integer> <key>Name</key><string>Yesterday</string> <key>Artist</key><string>The Beatles</string> <key>Composer</key><string>Lennon [John], McCartney [Paul]</string> <key>Album</key><string>Help!</string> </dict> --snip -- </dict> 6. <key>Playlists</key> <array> <dict> <key>Name</key><string>Now</string> <key>Playlist ID</key><integer>21348</integer> --snip -- <array> <dict> <key>Track ID</key><integer>6382</integer> </dict> --snip -- </array> </dict> </array> </dict> </plist>

属性列表（P-list）文件将对象表示为字典，<dict> 和 <key> 标签与这种方式有关。字典是把键和值关联起来的数据结构，让查找值变得容易。属性列表文件使用字典的字典，其中和键关联的值往往自身又是另一个词典（甚至一个字典列表）。

<xml>标签确定文件为XML文件。在这个开始标签之后，文档类型定义（DTD）定义了XML文档的结构1. 。如你所见，苹果在该标签中的统一资源定位符（URL）中定义了这种结构。

在2. 行，文件声明了顶层<plist>标签，其唯一子元素是字典<dict> 3. 。该字典包含了各种键，在4. 行，包括Major Version、Minor Version，等等，但我们的兴趣在5. 行的Tracks键。注意，该键对应的值也是一个字典，它将整数的音轨ID映射到另一个字典，其中包含Name、Artist等元素。音乐收藏中的每个音轨都有唯一的音轨ID键。

播放列表顺序在6. 行由Playlists定义，它是顶层字典的一个子节点。

## 1.3 代码该项目的目标是找到你的音乐收藏中的重复乐曲，确定播放列表之间共同的音轨，绘制音轨时长的分布图，以及歌曲评分和时长之间的关系图。

随着音乐收藏不断增加，你总会遇到重复的乐曲。为了确定重复的乐曲，查找与Tracks键关联的字典中的名称（前面讨论过），找到重复的乐曲，并用音轨长度作为附加准则来检测重复的乐曲，因为名称相同、但长度不同的音轨，可能是不一样的。

要找到两个或多个播放列表之间共同的音轨，你需要将音乐收藏导出为播放列表文件，收集每个播放列表的音轨名称，作为集合进行比较，通过发现集合的交集来找到共同的音轨。

在收集音乐收藏数据的同时，我们将使用强大的matplotlib（http://matplotlib.org/）绘图软件包来创建一些图，该软件包由已故的John Hunter开发。我们可以绘制直方图来显示音轨时长的分布，绘制散点图来比较乐曲评分与长度。

要查看完整的项目代码，请直接跳到1.4节。

### 1.3.1 查找重复首先可以用findDuplicates()方法来查找重复的曲目，如下所示： def findDuplicates(fileName): print('Finding duplicate tracks in %s...' % fileName) # read in a playlist 1. plist = plistlib.readPlist(fileName) # get the tracks from the Tracks dictionary 2. tracks = plist['Tracks'] # create a track name dictionary 3. trackNames = {} # iterate through the tracks 4. for trackId, track in tracks.items(): try: 5. name = track['Name'] duration = track['Total Time'] # look for existing entries 6. if name in trackNames: # if a name and duration match, increment the count # round the track length to the nearest second 7. if duration//1000 == trackNames[name][0]//1000: count = trackNames[name][1] 8. trackNames[name] = (duration, count+1) else: # add dictionary entry as tuple (duration, count) 9. trackNames[name] = (duration, 1) except: # ignore pass

在1. 行，readPlist()方法接受一个p-list文件作为输入，并返回顶层字典。在2. 行，访问Tracks字典，在3. 行，创建一个空的字典，用来保存重复的乐曲。在4. 行，开始用items()方法迭代Tracks字典，这是Python在迭代字典时取得键和值的常用方法。

在5. 行，取得字典中每个音轨的名称和时长。用in关键字，检查当前乐曲的名称是否已在被构建的字典中6. 。如果是这样的，程序检查现有的音轨和新发现的音轨长度是否相同7. ，用//操作符，将每个音轨长度除以1000，由毫秒转换为秒，并四舍五入到最接近的秒，以进行检查（当然，这意味着，只有毫秒差异的两个音轨被认为是相同的）。如果确定这两个音轨长度相等，就取得与name关联的值，这是（duration，count）元组，并在8. 行增加计数。如果这是程序第一次遇到的音轨名称，就创建一个新条目，count为19. 。

将代码的主for循环放在try语句块中，这是因为一些乐曲音轨可能没有定义乐曲名称。在这种情况下，跳过该音轨，在except部分只包含pass（什么也不做）。

### 1.3.2 提取重复利用以下代码，提取重复的音轨： # store duplicates as (name, count) tuples 1. dups = [] for k, v in trackNames.items(): 2. if v[1] > 1: dups.append((v[1], k)) # save duplicates to a file 3. if len(dups) > 0: print("Found %d duplicates. Track names saved to dup.txt" % len(dups)) else: print("No duplicate tracks found!") 4. f = open("dups.txt", "w") for val in dups: 5. f.write("[%d] %s\n" % (val[0], val[1])) f.close()

在1. 行，创建一个空列表，保存重复乐曲。接下来，迭代遍历trackNames字典，如果count（用v[1]访问，因为它是元组的第二个元素）大于12. ，则将元组（name，count）添加到列表中。在3. 行，程序打印它找到的信息，然后用open()方法将信息存入文件4. 。在5. 行，迭代遍历dups列表，写下重复的条目。

### 1.3.3 查找多个播放列表中共同的音轨现在，让我们来看看如何找到多个播放列表中共同的乐曲音轨： def findCommonTracks(fileNames): # a list of sets of track names 1. trackNameSets = [] for fileName in fileNames: # create a new set 2. trackNames = set() # read in playlist 3. plist = plistlib.readPlist(fileName) # get the tracks tracks = plist['Tracks'] # iterate through the tracks for trackId, track in tracks.items(): try: # add the track name to a set 4. trackNames.add(track['Name']) except: # ignore pass # add to list 5. trackNameSets.append(trackNames) # get the set of common tracks 6. commonTracks = set.intersection(*trackNameSets) # write to file if len(commonTracks) > 0: 7. f = open("common.txt", "w") for val in commonTracks: s = "%s\n" % val 8. f.write(s.encode("UTF-8")) f.close() print("%d common tracks found. " "Track names written to common.txt." % len(commonTracks)) else: print("No common tracks!")

首先，将播放列表的文件名列表传入findCommonTracks()，它创建一个空列表1. ，保存从每个播放列表创建的一组对象。然后程序迭代遍历列表中的每个文件。对每个文件，创建一个名为trackNames的Python set对象2. ，然后像在findDuplicates()中一样，用plistlib读入文件3. ，取得Tracks字典。接下来，迭代遍历该字典中的每个音轨，并添加trackNames对象4. 。程序读完一个文件中的所有音轨后，将这个集合加入trackNameSets5. 。

在6. 行，使用set.intersection()方法来获得集合之间共同音轨的集合（用Python*的运算符来展开参数列表）。如果程序发现集合之间的共同音轨，就将音轨名称写入一个文件。在7. 行，打开文件，接下来的两行代码完成写入。使用encode()来格式化输出，确保所有Unicode字符都正确处理8. 。

### 1.3.4 收集统计信息接下来，用plotStats()方法，针对这些音轨名称收集统计信息： def plotStats(fileName): # read in a playlist 1. plist = plistlib.readPlist(fileName) # get the tracks from the playlist tracks = plist['Tracks'] # create lists of song ratings and track durations 2. ratings = [] durations = [] # iterate through the tracks for trackId, track in tracks.items(): try: 3. ratings.append(track['Album Rating']) durations.append(track['Total Time']) except: # ignore pass # ensure that valid data was collected 4. if ratings == [] or durations == []: print("No valid Album Rating/Total Time data in %s." % fileName) return

这里的目标是收集评分和音轨时长，然后画一些图。在1. 行和接下来的代码行中，读取了播放列表文件，并访问Tracks字典。接下来，创建两个空列表，保存评分和时长2. （在iTunes播放列表中，评分是一个整数，范围是[0，100]）。迭代遍历音轨，在3. 行，将评分和时长添加到相应的列表中。最后，在4. 行检查完整性，确保从播放列表文件收集了有效数据。

### 1.3.5 绘制数据我们已准备好绘制一些数据了。 # scatter plot 1. x = np.array(durations, np.int32) # convert to minutes 2. x = x/60000.0 3. y = np.array(ratings, np.int32) 4. pyplot.subplot(2, 1, 1) 5. pyplot.plot(x, y, 'o') 6. pyplot.axis([0, 1.05*np.max(x), -1, 110]) 7. pyplot.xlabel('Track duration') 8. pyplot.ylabel('Track rating') # plot histogram pyplot.subplot(2, 1, 2) 9. pyplot.hist(x, bins=20) pyplot.xlabel('Track duration') pyplot.ylabel('Count') # show plot 10. pyplot.show()

在1. 行，利用numpy.array()（在代码中作为np导入），将音轨时长数据放到32位整数数组中。然后在2. 行，利用numpy，将一个操作应用于数组中的每个元素。在这个例子中，将每个以毫秒为单位的时长值除以值60×1000。在3. 行，将乐曲评分保存另一个numpy数组y中。

用matplotlib在同一图像上绘制两张图。在4. 行，提供给subplot()的参数（即，(2, 1, 1)）告诉matplotlib，该图应该有两行（2）一列（1），且下一个点应在第一行（1）。在5. 行，通过调用plot()创建一个点，并且o告诉matplotlib用圆圈来表示数据。

在6. 行，为x 轴和y 轴设置略微大一点儿的范围，以便在图和轴之间留一些空间。在7. 和8. 行，为x 轴和y 轴设置说明文字。

现在用matplotlib的方法hist()，在同一张图中的第二行中，绘制时长直方图9. 。bins参数设置了数据分区的个数，其中每分区用于添加在这个范围内的计数。最后，调用show()10. ，matplotlib在新窗口中显示出漂亮的图。

### 1.3.6 命令行选项现在，我们来看看该程序的main()方法如何处理命令行参数： def main(): # create parser descStr = """ This program analyzes playlist files (.xml) exported from iTunes. """ 1. parser = argparse.ArgumentParser(description=descStr) # add a mutually exclusive group of arguments 2. group = parser.add_mutually_exclusive_group() # add expected arguments 3. group.add_argument('--common', nargs='*', dest='plFiles', required=False) 4. group.add_argument('--stats', dest='plFile', required=False) 5. group.add_argument('--dup', dest='plFileD', required=False) # parse args 6. args = parser.parse_args() if args.plFiles: # find common tracks findCommonTracks(args.plFiles) elif args.plFile: # plot stats plotStats(args.plFile) elif args.plFileD: # find duplicate tracks findDuplicates(args.plFileD) else: 7. print("These are not the tracks you are looking for.")

本书的大多数项目都有命令行参数。不要尝试手工分析它们并搞得一团糟，要将这个日常的任务委派给Python的argparse模块。在1. 行，为此创建了一个ArgumentParser对象。该程序可以做三件不同的事情，如发现播放列表之间的共同音轨，绘制统计数据，或发现播放列表中重复的曲目。但是，一个时间程序只能做其中一件事，如果用户决定同时指定两个或多个选项，我们不希望它崩溃。argparse模块为这个问题提供了一个解决方案，即相互排斥的参数分组。在2. 行，用parser.add_mutually_exclusive_group()方法来创建这样一个分组。

在3. 、4. 和5. 行，指定了前面提到的命令行选项，并输入应该将解析值存入的变量名（args.plFiles、args.plFile和args.plFileD），实际解析在6. 行完成。参数解析后，就将它们传递给相应的函数，findCommonTracks()、plotStats()和findDuplicates()，本章前面讨论过这些函数。

要查看参数是否被解析，就测试args中相应的变量名。例如，如果用户没有使用--common选项（该选项找出播放列表之间的共同音轨），解析后args.plFiles应该设置为None。

在7. 行，处理用户未输入任何参数的情况。

## 1.5 运行程序下面是该程序的运行示例：$ python playlist.py --common test-data/maya.xml test-data/rating.xml

下面是输出：5 common tracks found. Track names written to common.txt. $ cat common.txt God Shuffled His Feet Rubric Floe Stairway To Heaven Pi's Lullaby moksha:playlist mahesh$

现在，让我们绘制这些音轨的一些统计数据。$ python playlist.py --stats test-data/rating.xml

图1-1展示了这次运行的输出。

图1-1 playlist.py运行示例

## 1.7 实验下面有一些方法可以扩展这个程序。

1．发现重复音轨时，考虑了以音轨时长作为附加标准，来确定两个音轨是否相同。但寻找共同的音轨时，只用了音轨名称进行比较。在findCommonTracks()中，请结合音轨时长作为额外的检查。

2．在plotStats()方法中，用了matplotlib的hist()方法来计算和显示柱状图。请编写代码手动计算直方图，不用hist()方法显示。要将结果显示为条形图，请阅读matplotlib文档中条形图的部分。

3．有一些数学公式用于计算相关系数，测量两个变量之间的关系强度。阅读相关性的资料，利用你自己的音乐数据，计算评分/时长散点图中的相关系数。请考虑可以利用播放列表中收集的数据，制作出另外那些散点图。

# 第2章万花尺我们可以用万花尺玩具（如图2-1所示）来绘制数学曲线。这种玩具由两个不同尺寸的塑料齿轮组成，一大一小。小的齿轮有几个孔。把钢笔或铅笔放入一个孔，然后在较大齿轮（内部有齿）内旋转里面的小齿轮，保持笔与外轮接触，可以画出无数复杂而奇妙的对称图案。

在这个项目中，我们将用Python来创建动画，像万花尺一样绘制曲线。我们的spiro.py程序将用Python和参数方程来描述程序的万花尺齿轮的运动，并绘制曲线（我称之为螺线）。我们可以将完成的画图保存为PNG图像文件，并用命令行选项来指定参数或生成随机螺线。

在这个项目中，我们将学习如何在计算机上绘制螺线。还将学习以下几点：

- 用turtle模块创建图形；

- 使用参数方程；

- 利用数学方程来生成曲线；

- 用线段来画曲线；

- 用定时器来生成图形动画；

- 将图形保存为图像文件。

图2-1 万花尺关于这个项目要注意：我在这个项目中选择了turtle模块用于说明展示，因为它很有趣，但turtle比较慢，如果性能很关键，就不适合用它来创建图形（你对海龟有何期望？）。如果想快速画图，有更好的方法，后面的项目将探索一些可选方案。

## 2.1 参数方程在本节中，你将看到用参数方程来画圆的简单例子。参数方程将曲线上点的坐标表示为一个变量的函数，该变量称为参数。参数方程让绘制曲线变得容易，因为只要将参数代入方程就能产生曲线。

注意如果你现在不想学习这部分数学知识，可以跳到下一部分，讨论针对万花尺项目的方程。

我们开始考虑用半径r 来描述一个圆的方程，圆心位于二维平面的原点。x 、y 坐标满足该方程的所有点构成了圆。

现在，请考虑下面的方程：

x = r cos(θ )

y = r sin(θ )

这些方程是圆的参数表示，其中角θ 是参数。这些方程中（X，Y）的任何值，都满足前面描述的圆的方程，X2 + Y2 = R2 。如果让θ 从0变到2π，可以用这些方程来计算圆上对应的x 和y 坐标。图2-2展示了这种方案。

图2-2 用参数方程描述圆记住，这两个方程适用于圆心在坐标系原点的圆。将圆心转换到点(a , b )，就可以将圆置于xy 平面的任何位置。所以更一般的参数方程就变成x = a + r cos(θ )和y = b + r cos(θ )。现在，让我们来看看描述螺线的方程。

### 2.1.1 万花尺方程图2-3展示了类似万花尺运动的数学模型。该模型没有齿轮，因为玩具中的齿轮只是为了防止打滑，而在这里不必担心打滑。

图2-3 万花尺数学模型在图2-3中，C是较小的圆的圆心，P是笔尖。较大的圆半径为R ，较小的圆半径为r 。半径之比表示如下：

将线段PC与小圆半径r 之比作为变量l（l = PC / r ），它决定了笔尖离小圆圆心有多远。然后，组合这些变量来表示P的运动，得到如下的参数方程：

注意这些曲线称为内旋轮线和外旋轮线。虽然方程可能看起来有点吓人，但推导是非常简单的。如果你想探索其中的数学，请参见维基百科。[1]

图2-4展示了如何用这些方程，基于参数的变化，产生一条曲线。通过改变参数R 、r 和l ，可以产生变化无穷的迷人曲线。

图2-4 示例曲线将曲线绘制为一系列点之间的线段。如果这些点足够接近，图看起来就像平滑的曲线。真正玩过万花尺就知道，这取决于使用的参数，万花尺可能需要许多转数来完成。要确定何时停止绘图，就要利用万花尺的周期性（即万花尺图案多久开始重复），研究内外圆的半径之比：

分子分母除以它们的最大公约数（GCD），化简该分数，分子就告诉我们需要多少圈才能完成曲线。例如，在图2-4中，(r , R )的GCD是5。

下面是该分数化简后的形式：

这告诉我们，13圈后，曲线将开始重复。44告诉我们小圆围绕其中心旋转的圈数，它提示了曲线的形状。在图2-4中数一下，会看到图形中花瓣或叶的数目恰好是44！

一旦用简化形式表示了半径比r /R ，画出螺线的参数θ 范围就是[0，2πr]。这告诉我们何时停止绘制特定的螺线。不知道该角度的结束范围，就会循环不止，不必要地重复该曲线。

### 2.1.2 海龟画图我们可以用Python的turtle模块来创建图案。这是一个简单的绘图程序，模型是一只海龟拖着尾巴穿过沙滩，留下图案。turtle模块包括了一些方法，用于设置笔（海龟的尾巴）的位置和颜色，以及其他有用的绘图函数。如你所见，只要少量绘图函数，就可以创建漂亮的螺线。

例如，这个程序用turtle画圆。输入以下代码，保存为drawcircle.py，在Python中运行它： import math 1. import turtle # draw the circle using turtle def drawCircleTurtle(x, y, r): # move to the start of circle 2. turtle.up() 3. turtle.setpos(x + r, y) 4. turtle.down() # draw the circle 5. for i in range(0, 365, 5): 6. a = math.radians(i) 7. turtle.setpos(x + r*math.cos(a), y + r*math.sin(a)) 8. drawCircleTurtle(100, 100, 50) 9. turtle.mainloop()

在1. 行，从导入turtle模块开始。接下来，定义drawCircleTurtle()方法，它在2. 行调用up()。这告诉Python提笔。换句话说，让笔离开虚拟的纸，这样移动海龟也不会画图。开始绘图之前，先定位海龟。

在3. 行，将海龟的位置设置为横轴上的第一个点：(x + r, y)，其中(x，y)是该圆的圆心。现在准备好画图了，所以在4. 行调用down()。在5. 行，利用range(0, 365, 5)开始循环，以5为步长递增变量i，从0到360，变量i是角度参数，将传入圆的参数方程，但首先在6. 行将它从度转为弧度（大多数计算机程序的角度计算需要弧度）。

在7. 行，利用前面讨论过的参数方程计算圆的坐标，并设置相应的海龟位置，这样就从海龟上一个位置画线到新计算的位置（从技术上讲，产生的是N边多边形，但因为用了很小的角度，N将非常大，多边形看起来像一个圆）。

在8. 行，调用drawCircleTurtle()来画圆，在9. 行，调用mainloop()，它保持tkinter窗口打开，让你可以欣赏你画的圆（Tkinter是Python默认的GUI库）。

现在，我们准备好画一些螺线了！

## 2.2 所需模块我们将利用下面的模块创建螺线：

- turtle模块用于绘图；

- pillow，这是Python图像库（PIL）的一个分支，用于保存螺线图像。

## 2.3 代码首先，定义类Sipro，来绘制这些曲线。我们会用这个类一次画一条曲线（利用draw()方法），并利用一个定时器和update()方法，产生一组随机螺线的动画。为了绘制Spiro对象并产生动画，我们将使用SpiroAnimator类。

要查看完整的项目代码，请直接跳到2.4节。

### 2.3.1 Spiro构造函数下面是Spiro构造函数： # a class that draws a Spirograph class Spiro: # constructor def __init__(self, xc, yc, col, R, r, l): # create the turtle object 1. self.t = turtle.Turtle() # set the cursor shape 2. self.t.shape('turtle') # set the step in degrees 3. self.step = 5 # set the drawing complete flag 4. self.drawingComplete = False # set the parameters 5. self.setparams(xc, yc, col, R, r, l) # initialize the drawing 6. self.restart()

在1. 行，Spiro构造函数创建一个新的turtle对象，这将有助于我们同时绘制多条螺线。在2. 行，将光标的形状设置为海龟（在https://docs.python.org/3.3/library/ turtle.html ，你可以在turtle文档中找到其他选项）。在3. 行，将参数绘图角度的增量设置为5度，在4. 行，设置了一个标志，将在动画中使用它，它会产生一组螺线。

在5. 和6. 行，调用设置函数，接下来讨论该函数。

### 2.3.2 设置函数现在让我们看看getParams()方法，它帮助初始化Spiro对象，如下所示： # set the parameters def setparams(self, xc, yc, col, R, r, l): # the Spirograph parameters 1. self.xc = xc self.yc = yc 2. self.R = int(R) self.r = int(r) self.l = l self.col = col # reduce r/R to its smallest form by dividing with the GCD 3. gcdVal = gcd(self.r, self.R) 4. self.nRot = self.r//gcdVal # get ratio of radii self.k = r/float(R) # set the color self.t.color(*col) # store the current angle 5. self.a = 0

在1. 行，保存曲线中心的坐标。然后在2. 行，将每个圆的半径（R 和r ）转换为整数并保存这些值。在3. 行，用Python模块fractions内置的gcd()方法来计算半径的GCD。我们将用这些信息来确定曲线的周期性，在4. 行将它保存为self.nRot。最后，在5. 行，保存当前的角度，我们将用它来创建动画。

### 2.3.3 restart()方法接下来，restart()方法重置Spiro对象的绘制参数，让它准备好重画： # restart the drawing def restart(self): # set the flag 1. self.drawingComplete = False # show the turtle 2. self.t.showturtle() # go to the first point 3. self.t.up() 4. R, k, l = self.R, self.k, self.l a = 0.0 5. x = R*((1-k)*math.cos(a) + l*k*math.cos((1-k)*a/k)) y = R*((1-k)*math.sin(a) - l*k*math.sin((1-k)*a/k)) 6. self.t.setpos(self.xc + x, self.yc + y) 7. self.t.down()

这里用了布尔标志drawingComplete，来确定绘图是否已经完成，在1. 行初始化该标志。绘制多个Spiro对象时，这个标志是有用的，因为它可以追踪某个特定的螺线是否完成。在2. 行，显示海龟光标，以防它被隐藏。在3. 行提起笔，这样就可以在6. 行移动到第一个位置而不画线。在4. 行，使用了一些局部变量，以保持代码紧凑。然后，在5. 行，计算角度a设为0时的x 和y 坐标，以获得曲线的起点。最后，在7. 行，我们已完成，并落笔。Setpos()调用将绘制实际的线。

### 2.3.4 draw()方法

draw()方法用连续的线段绘制该曲线。 # draw the whole thing def draw(self): # draw the rest of the points R, k, l = self.R, self.k, self.l 1. for i in range(0, 360*self.nRot + 1, self.step): a = math.radians(i) 2. x = R*((1-k)*math.cos(a) + l*k*math.cos((1-k)*a/k)) y = R*((1-k)*math.sin(a) - l*k*math.sin((1-k)*a/k)) self.t.setpos(self.xc + x, self.yc + y) # drawing is now done so hide the turtle cursor 3. self.t.hideturtle()

在1. 行，迭代遍历参数i的完整范围，它以度表示，是360乘以nRot。在2. 行，计算参数i的每个值对应的X 和Y 坐标。在3. 行，隐藏光标，因为我们已完成绘制。

### 2.3.5 创建动画

update()方法展示了一段一段绘制曲线来创建动画时所使用的绘图方法。 # update by one step def update(self): # skip the rest of the steps if done 1. if self.drawingComplete: return # increment the angle 2. self.a += self.step # draw a step R, k, l = self.R, self.k, self.l # set the angle 3. a = math.radians(self.a) x= self.R*((1-k)*math.cos(a) + l*k*math.cos((1-k)*a/k)) y = self.R*((1-k)*math.sin(a) - l*k*math.sin((1-k)*a/k)) self.t.setpos(self.xc + x, self.yc + y) # if drawing is complete, set the flag 4. if self.a >= 360*self.nRot: self.drawingComplete = True # drawing is now done so hide the turtle cursor self.t.hideturtle()

在1. 行，update()方法检查drawingComplete标志是否设置。如果没有设置，则继续执行代码其余的部分。在2. 行，update()增加当前的角度。从3. 行开始，它计算当前角度对应的（X，Y）位置并将海龟移到那里，在这个过程中画出线段。

讨论万花尺方程时，我提到了曲线的周期性。在一定的角度后，万花尺的图案开始重复。在4. 行，检查角度是否达这条特定曲线计算的完整范围。如果是这样，就设置drawingComplete标志，因为绘图完成了。最后，隐藏海龟光标，你可以看到自己美丽的创作。

### 2.3.6 SpiroAnimator类

SpiroAnimator类让我们同时绘制随机的螺线。该类使用一个计时器，每次绘制曲线的一段。这种技术定期更新图像，并允许程序处理事件，如按键、鼠标点击，等等。但是，这种计时器技术需要对绘制代码进行一些调整。 # a class for animating Spirographs class SpiroAnimator: # constructor def __init__(self, N): # set the timer value in milliseconds 1. self.deltaT = 10 # get the window dimensions 2. self.width = turtle.window_width() self.height = turtle.window_height() # create the Spiro objects 3. self.spiros = [] for i in range(N): # generate random parameters 4. rparams = self.genRandomParams() # set the spiro parameters 5. spiro = Spiro(*rparams) self.spiros.append(spiro) # call timer 6. turtle.ontimer(self.update, self.deltaT)

在1. 行，该SpiroAnimator构造函数将DeltaT设置为10，这是以毫秒为单位的时间间隔，将用于定时器。在2. 行，保存海龟窗口的尺寸。然后在3. 行创建一个空数组，其中将填入一些Spiro对象。这些封装的万花尺绘制，然后循环N次（N传入给构造函数SpiroAnimator），在5. 行创建一个新的Spiro对象，并将它添加到Spiro对象的列表中。这里的rparams是一个元组，需要传入到Spiro构造函数。但是，构造函数需要一个参数列表，所以用Python的*运算符将元组转换为参数列表。

最后，在6. 行，设置turtle.ontimer()方法每隔DeltaT毫秒调用update()。

请注意，在4. 行调用了一个辅助方法，名为genRandomParams()。接下来就看看这个方法。

### 2.3.7 genRandomParams()方法我们用genRandomParams()方法来生成随机参数，在每个Spiro对象创建时发送给它，来生成各种曲线。 # generate random parameters def genRandomParams(self): width, height = self.width, self.height 1. R = random.randint(50, min(width, height)//2) 2. r = random.randint(10, 9*R//10) 3. l = random.uniform(0.1, 0.9) 4. xc = random.randint(-width//2, width//2) 5. yc = random.randint(-height//2, height//2) 6. col = (random.random(), random.random(), random.random()) 7. return (xc, yc, col, R, r, l)

为了生成随机数，利用来自Python的random模块的两个方法：randint()，它返回指定范围内的随机整数，以及uniform()，它对浮点数做同样的事。在1. 行，将R设置为50至窗口短边一半长度的随机整数，在2. 行，将r设置为R的10%至90%之间。

然后，在3. 行，将l设置为0.1至0.9之间的随机小数。在4. 和5. 行，在屏幕边界内随机选择x 和y 坐标，选择屏幕上的一个随机点作为螺线的中心。在6. 行随机设置为红、绿和蓝颜色的成分，为曲线指定随机的颜色。最后，在7. 行，所有计算的参数作为一个元组返回。

### 2.3.8 重新启动程序我们将用另一个restart()方法来重新启动程序。

# restart spiro drawing def restart(self): for spiro in self.spiros: # clear spiro.clear() # generate random parameters rparams = self.genRandomParams() # set the spiro parameters spiro.setparams(*rparams) # restart drawing spiro.restart()

它遍历所有的Spiro对象，清除以前绘制的每条螺线，分配新的螺线参数，然后重新启动程序。

### 2.3.9 update()方法下面的代码展示了SproAnimator中的update()方法，它由定时器调用，以动画的形式更新所有的Spiro对象： def update(self): # update all spiros 1. nComplete = 0 for spiro in self.spiros: # update 2. spiro.update() # count completed spiros 3. if spiro.drawingComplete: nComplete += 1 # restart if all spiros are complete 4. if nComplete == len(self.spiros): self.restart() # call the timer 5. turtle.ontimer(self.update, self.deltaT)

update()方法使用一个计数器nComplete来记录已画的Spiro对象的数目。在1. 行初始化后，它遍历Spiro对象的列表，在2. 行更新它们，如果一个Spiro完成，就在3. 行将计数器加1。

在循环外的4. 行，检查计数器，看看是否所有对象都已画完。如果已画完，调用restart()方法重新开始新的螺线动画。在5. 行restart()的末尾，调用计时器方法，它在DeltaT毫秒后再次调用update()。

### 2.3.10 显示或隐藏光标最后，使用下面的方法来打开或关闭海龟光标。这可以让绘图更快。 # toggle turtle cursor on and off def toggleTurtles(self): for spiro in self.spiros: if spiro.t.isvisible(): spiro.t.hideturtle() else: spiro.t.showturtle()

### 2.3.11 保存曲线使用saveDrawing()方法，将绘制保存为PNG图像文件。 # save drawings as PNG files def saveDrawing(): # hide the turtle cursor 1. turtle.hideturtle() # generate unique filenames 2. dateStr = (datetime.now()).strftime("%d%b%Y-%H%M%S") fileName = 'spiro-' + dateStr print('saving drawing to %s.eps/png' % fileName) # get the tkinter canvas 3. canvas = turtle.getcanvas() # save the drawing as a postscipt image 4. canvas.postscript(file = fileName + '.eps') # use the Pillow module to convert the postscript image file to PNG 5. img = Image.open(fileName + '.eps') 6. img.save(fileName + '.png', 'png') # show the turtle cursor 7. turtle.showturtle()

在1. 行，隐藏海龟光标，这样就不会在最后的图形中看到它。然后，在2. 行，使用datetime()，利用当前时间和日期（以"日-月-年-时-分-秒"的格式），以生成图像文件的唯一名称。将这个字符串加在spiro-后面，生成文件名。

turtle程序采用tkinter创建的用户界面（UI）窗口，在3. 和4. 行，利用tkinter的canvas对象，将窗口保存为嵌入式PostScript（EPS）文件格式。由于EPS是矢量格式，你可以用高分辨率打印它，但PNG用途更广，所以在5. 行用Pillow打开EPS文件，并在6. 行将它保存为PNG文件。最后，在7. 行，取消隐藏海龟光标。

### 2.3.12 解析命令行参数和初始化像第1章中一样，在main()方法中用argparse来解析传入程序的命令行选项。1. parser = argparse.ArgumentParser(description=descStr) # add expected arguments 2. parser.add_argument('--sparams', nargs=3, dest='sparams', required=False, help="The three arguments in sparams: R, r, l.") # parse args 3. args = parser.parse_args()

在1. 行，创建参数解析器对象，在2. 行，向解析器添加--sparams可选参数。在3. 行，调用函数进行实际的解析。

接下来，代码设置了一些turtle参数。 # set the width of the drawing window to 80 percent of the screen width 1. turtle.setup(width=0.8) # set the cursor shape to turtle 2. turtle.shape('turtle') # set the title to Spirographs! 3. turtle.title("Spirographs!") # add the key handler to save our drawings 4. turtle.onkey(saveDrawing, "s") # start listening 5. turtle.listen() # hide the main turtle cursor 6. turtle.hideturtle()

在1. 行，用setup()将绘图窗口的宽度设置为80％的屏幕宽度（你也可以给setup指定高度和原点参数）。在2. 行，设置光标形状为海龟，在3. 行，设置程序窗口的标题为Spirographs！，在4. 行，利用onkey()和saveDrawing，在按下S时保存图画。然后，在5. 行，调用listen()让窗口监听用户事件。最后，在6. 行，隐藏海龟光标。

命令行参数解析后，代码的其余部分进行如下： # check for any arguments sent to --sparams and draw the Spirograph 1. if args.sparams: 2. params = [float(x) for x in args.sparams] # draw the Spirograph with the given parameters col = (0.0, 0.0, 0.0) 3. spiro = Spiro(0, 0, col, *params) 4. spiro.draw() else: # create the animator object 5. spiroAnim = SpiroAnimator(4) # add a key handler to toggle the turtle cursor 6. turtle.onkey(spiroAnim.toggleTurtles, "t") # add a key handler to restart the animation 7. turtle.onkey(spiroAnim.restart, "space") # start the turtle main loop 8. turtle.mainloop()

在1. 行，首先检查是否有参数赋给--sparams。如果有，就从字符串中提取它们，用"列表解析"将它们转换成浮点数2. （列表解析是一种Python结构，让你以紧凑而强大的方式创建一个列表，例如，a = [2*x for x in range(1, 5)]创建前4个偶数的列表）。

在3. 行，利用任何提取的参数来构造Spiro对象（利用Python的*运算符，它将列表转换为参数）。然后，在4. 行，调用draw()，绘制螺线。

现在，如果命令行上没有指定参数，就进入随机模式。在5. 行，创建一个SpiroAnimator对象，向它传入参数4，告诉它创建4幅图画。在6. 行，利用onkey()来捕捉按键T，这样就可以用它来切换海龟光标（toggleTurtles），在7. 行，处理空格键（space），这样就可以用它在任何时候重新启动动画。最后，在8. 行，调用mainloop()告诉tkinter窗口保持打开，监听事件。

## 2.5 运行万花尺动画现在该运行程序了。$ python spiro.py

默认情况下，spiro.py程序绘制随机螺线，如图2-5所示。按S键保存绘制。

图2-5 spiro.py的运行示例现在，再次运行程序，这次在命令行传入参数，画出特定的螺线。$ python spiro.py --sparams 300 100 0.9

图2-6展示了输出结果。如你所见，这段代码根据用户指定的参数绘制了一条螺线，图2-5和它不同，展示了几个随机螺线的动画。

图2-6 用具体参数运行spiro.py的示例

## 2.7 实验下面有一些方法可以进一步尝试螺线。

1．现在你已知道如何画圆，请写一个程序来绘制随机的对数螺线。找到参数形式的对数螺线方程，然后用它来绘制螺线。

2．你可能已经注意到，画曲线时，海龟光标总是朝右，但这不是海龟移动的方式！请调整海龟的方向，在绘制曲线时，让它朝向绘制的方向（提示：每步计算连续点之间的方向矢量，用turtle.setheading()方法来调整海龟的方向）。

3．尝试用海龟绘制Koch snowflake（科赫雪花），它是利用递归（即调用自身的函数）的分形曲线。可以像这样组织递归函数调用：

# recursive Koch snowflake def kochSF(x1, y1, x2, y2, t): # compute intermediate points p2, p3 if segment_length > 10: # recursively generate child segments # flake #1 kochSF(x1, y1, p1[0], p1[1], t) # flake #2 kochSF(p1[0], p1[1], p2[0], p2[1], t) # flake #3 kochSF(p2[0], p2[1], p3[0], p3[1], t) # flake #4 kochSF(p3[0], p3[1], x2, y2, t) else: # draw # ...

如果你确实遇到困难，可以在http://electronut.in/koch-snowflake-and-the-thue- morse-sequence/ 找到我的解决方案。

[1]http://en.wikipedia.org/wiki/Spirograph/"。

# 第二部分模拟生命

"首先，我们假设奶牛是一个球体。"

--佚名物理学笑话

# 第3章 Conway生命游戏你可以用计算机来研究一个系统，方法是建立该系统的数学模型，编程表示该模型，然后让该模型随着时间的推移而演进。有很多种计算机模拟，但我会专注于一个著名的模拟，即Conway生命游戏，它是英国数学家John Conway的成果。生命游戏是细胞自动机，即网格上的一组彩色细胞，根据定义相邻细胞状态的一组规则，经过一些时间逐步演进。

这个项目将创建一个N×N的细胞网格，通过应用Conway生命游戏的规则，模拟系统随时间的演进。你将显示每个时间段的游戏状态，并提供一些方式将输出保存到文件。你会设置系统的初始状态，要么是随机分布，要么是预先设计的图案。

该模拟由以下几部分组成：

- 在一维或两维空间中定义的属性；

- 在模拟中的每一步，改变这种属性的数学规则；

- 随着系统的演进，显示或记录系统状态的方式。

在Conway生命游戏中的细胞可以处于ON或OFF状态。游戏从一个初始状态开始，其中每个细胞分配一个状态，数学规则决定其状态如何随时间而改变。Conway生命游戏中令人惊奇的是，只有4个简单的规则，系统演进会产生行为极其复杂的图案，仿佛它们是活的。图案包括"滑翔机"，即在网格上滑动，"眨眼"，即闪烁ON和OFF，甚至还有复制图案。

当然，这个游戏的哲学意义也很重要，因为它们表明，复杂的结构可以根据简单的规则演进，不必遵循任何一种预设的模式。

下面是该项目包含的一些主要概念：

- 利用matplotlib imshow来展示数据的二维网格；

- 利用matplotlib生成动画；

- 使用numpy数组；

- 将%运算符用于边界条件；

- 设置值的随机分布。

## 3.1 工作原理因为生命游戏建立在9个方格的网格中，每个细胞有8个相邻细胞，如图3-1所示。模拟中的给定细胞(i, j)用二维数组[i][j]来存取，其中i和j分别是行和列的下标。在给定时间段，给定细胞的值取决于前一时间段它的邻居的状态。Conway生命游戏有4个规则。

1．如果一个细胞为ON，邻居中少于两个为ON，它变为OFF。

2．如果一个细胞为ON，邻居中有两个或3个为ON，它保持为ON。

3．如果一个细胞为ON，邻居中超过3个为ON，它变为OFF。

4．如果一个细胞为OFF，邻居中恰好有3个为ON，它变为ON。

图3-1 8个相邻细胞这些规则是为了反映一些基本方式，即一群生物体随时间推移的遭遇：如果细胞邻居少于2或多于3，种群太少或种群太多都会杀死细胞，将细胞变为OFF；如果种群平衡，细胞保持为ON并繁殖，将另一个细胞从OFF变为ON。但是，在网格边缘的细胞呢？哪些细胞是自己的邻居？要回答这个问题，就要考虑边界条件，决定细胞在网格边缘或边界时的规则。我将采用环形边界条件，这意味着正方形网格卷起来，构成一个环面，从而解决这个问题。如图3-2所示，网格先卷起来，使它的水平边缘（A和B）相连，形成一个圆柱体，然后圆柱体的垂直边缘（C和D）相连，以形成一个环面。形成环面后，所有细胞都有邻居，因为整个空间没有边缘。

图3-2 环型边界条件的概念视图注意这类似于Pac-Man（吃豆子）在边界的工作方式。如果超出了屏幕的顶部，就会重新在底部出现。如果超出了屏幕的左侧，就会重新在右侧出现。这种边界条件在二维模拟中很常见。

以下是算法描述，我们用它来应用这4个规则，并运行模拟。

1．初始化网格中的细胞。

2．在模拟的每个时间段，对于网格中每个细胞(i, j)，做下面的事：

a．根据它的邻居更新细胞(i, j)的值，同时考虑到边界条件；

b．更新网格值的显示。

## 3.3 代码我们将在Python解释器中一点一点地为模拟编写代码，考察不同部分所需的代码片段。要查看完整的项目代码，请直接跳到3.4节。

首先，导入该项目使用的模块：>>> import numpy as np >>> import matplotlib.pyplot as plt >>> import matplotlib.animation as animation

现在让我们创建网格。

### 3.3.1 表示网格为了在网格上表示细胞的活（ON）或死（OFF），分别用255和0作为ON和OFF的值。我们将采用matplotlib的imshow()方法，来显示网格当前的状态，将一个数字矩阵表示为一张图像。请输入以下内容：1. >>> x = np.array([[0, 0, 255], [255, 255, 0], [0, 255, 0]]) 2. >>> plt.imshow(x, interpolation='nearest') plt.show()

在1. 行，定义了3×3的二维numpy数组，数组中的每个元素是一个整数值。然后，在2. 行，用plt.show()方法将这个矩阵的值显示为图像，并给interpolation选项传入'nearest'值，以得到尖锐的边缘（否则是模糊的）。

图3-3展示了这段代码的输出。

图3-3 显示网格的值注意，0（OFF）显示为暗灰色，255（ON）显示为浅灰色，这是imshow()使用的默认颜色。

### 3.3.2 初始条件要开始模拟，先为二维网格中的每个细胞设置一个初始状态。可以使用ON和OFF细胞的随机分布，看看会出现怎样的图案，或者添加一些特定的图案，看看它们如何发展。我们将探讨这两种方法。

要采用随机的初始状态，就使用numpy中random模拟的choice()方法。输入以下内容：np.random.choice([0, 255], 4*4, p=[0.1, 0.9]).reshape(4, 4)

下面是输出：array([[255, 255, 255, 255], [255, 255, 255, 255], [255, 255, 255, 255], [255, 255, 255, 0]])

np.random.choice从给定的列表[0,255]中选择一个值，每个值出现的概率由参数p=[0.1, 0.9]指定。这里，你要求0出现的概率是0.1（或10%），255出现的概率是90%（p中两个值相加必须等于1）。因为这个choice()方法创建了16个值的一维数组，所以用.reshape使它成为一个二维数组。

要建立初始条件来匹配特定图案，而不是只填入一组随机值，就将二维网格初始化为零，然后用一个方法在网格的特定行和列增加一个图案，如下所示：def addGlider(i, j, grid): """adds a glider with top left cell at (i, j)""" 1. glider = np.array([[0, 0, 255], [255, 0, 255], [0, 255, 255]]) 2. grid[i:i+3, j:j+3] = glider 3. grid = np.zeros(N*N).reshape(N, N) 4. addGlider(1, 1, grid)

在1. 行，用3×3的numpy数组定义了滑翔机图案（看上去是一种在网格中平稳穿越的图案）。在2. 行，可以看到如何用numpy的切片操作，将这种图案数组复制到模拟的二维网格中，它的左上角放在i和j指定的坐标。在3. 行，创建N×N的零值数组，在4. 行，调用addGlider()方法，初始化带有滑翔机图案的网格。

### 3.3.3 边界条件现在，我们可以想一下如何实现环形边界条件。首先，让我们看看在N×N网格的右边缘会发生什么情况。i行最后一个细胞用grid[i][N-1]来访问。它右侧的邻居是grid[i][N]，但根据环形边界条件，grid[i][N]访问的值应该由grid[i][0]代替。下面是一种实现方法：if j == N-1: right = grid[i][0] else: right = grid[i][j+1]

当然，需要在网格的左侧，顶部和底部应用类似的边界条件，但这样做要加入许多代码，因为需要检测网格的4个边缘。更简洁的方式是用Python的取模（%）运算符，如下所示：>>> N = 16 >>> i1 = 14 >>> i2 = 15 >>> (i1+1)%N 15 >>> (i2+1)%N 0

如你所见，%运算符给出整数除以N的余数。可以用这个运算符让值在边缘折返，像这样重写网格访问代码：right = grid[i][(j+1)%N]

现在，如果一个细胞在网格边缘（换言之，如果j= N-1），用这种方法请求右边的细胞就会得到(j +1) %N，这将j设回0，让网格右侧卷曲到左侧。如果在网格底部做同样的事，它就折返到顶部。

### 3.3.4 实现规则生命游戏的规则基于相邻细胞的ON或OFF数目。为了简化这些规则的应用，可以计算出处于ON状态的相邻细胞总数。因为ON状态的值为255，所以可以对所有相邻细胞的值求和，再除以255，来获得ON细胞的数量。下面是相关的代码： # apply Conway's rules if grid[i, j] == ON: 1. if (total < 2) or (total > 3): newGrid[i, j] = OFF else: if total == 3: 2. newGrid[i, j] = ON

在1. 行，如果少于2个相邻细胞为ON或多于3个相邻细胞为ON，该细胞就由ON变成OFF。2. 行代码仅适用于OFF细胞：如果恰好有3个相邻细胞为ON，该细胞就变成ON。

现在该编写模拟的完整代码了。

### 3.3.5 向程序发送命令行参数下面的代码向程序发送命令行参数：

# main() function def main(): # command line argumentss are in sys.argv[1], sys.argv[2], ... # sys.argv[0] is the script name and can be ignored 1. # parse arguments parser = argparse.ArgumentParser(description="Runs Conway's Game of Life simulation.") # add arguments 2. parser.add_argument('--grid-size', dest='N', required=False) 3. parser.add_argument('--mov-file', dest='movfile', required=False) 4. parser.add_argument('--interval', dest='interval', required=False) 5. parser.add_argument('--glider', action='store_true', required=False) args = parser.parse_args()

main()函数首先定义了程序的命令行参数。在1. 行，用argparse类为代码添加命令行选项，然后在接下来几行中添加各种选项。在2. 行，指定模拟网格的大小N。在3. 行，指定保存.mov文件的名称。在4. 行，设置动画更新间隔的毫秒数。在5. 行，用滑翔机图案开始模拟。

### 3.3.6 初始化模拟继续看代码，接下来一段，对模拟初始化： # set grid size N = 100 if args.N and int(args.N) > 8: N = int(args.N) # set animation update interval updateInterval = 50 if args.interval: updateInterval = int(args.interval) # declare grid 1. grid = np.array([]) # check if "glider" demo flag is specified if args.glider: grid = np.zeros(N*N).reshape(N, N) addGlider(1, 1, grid) else: # populate grid with random on/off - more off than on grid = randomGrid(N)

仍在main()函数内，命令行选项解析后，这部分代码应用命令行传入的所有参数。例如，1. 行后的几行设置初始条件，要么是默认的随机图案，要么是滑翔机图案。最后，设置动画。 # set up the animation 1. fig, ax = plt.subplots() img = ax.imshow(grid, interpolation='nearest') 2. ani = animation.FuncAnimation(fig, update, fargs=(img, grid, N, ), frames=10, interval=updateInterval, save_count=50) # number of frames? # set the output file if args.movfile: ani.save(args.movfile, fps=30, extra_args=['-vcodec', 'libx264']) plt.show()

在1. 行，配置matplotlib的绘图和动画参数。在2. 行，animation.FuncAnimation()调用函数update()，该函数在前面的程序中定义，根据Conway生命游戏的规则，采用环形边界条件来更新网格。

## 3.5 运行模拟人生的游戏现在运行代码：$ python3 conway.py

这里采用模拟的默认参数：100×100个细胞的网格，50毫秒的更新间隔。观看模拟时，你会看到它如何进行，随着时间的推移创建并保持各种图案，如图3-4所示。

图3-4 进行中的生命游戏图3-5展示了模拟中可以寻找的一些图案。除了滑翔机，请寻找3细胞的闪光灯，以方块或面包的形状等静态图案。

现在，改变一下，用这些参数来运行模拟：$ python conway.py --grid-size 32 --interval 500 --glider

这创建了32×32的模拟网格，每500毫秒更新动画，并采用初始的滑翔机图案，如图3-5的右下图所示。

图3-5 生命游戏中的图案

## 3.6 小结这个项目探讨了Conway生命游戏。我们学习了如何基于某些规则，来建立基本的计算机模拟，以及如何用matplotlib，随着系统的演进，让系统的状态可视化。

我们的Conway生命游戏实现更强调简单，而不是性能。有许多不同的方式可以加快生命游戏的计算，关于如何做到这一点，有大量的研究。快速在互联网搜索一下，会发现很多这样的研究。

## 3.7 实验下面有一些方法，可以进一步试验Conway生命游戏。

1．编写addGosperGun()方法，在网格中添加如图3-6所示的图案。这种图案被称为"高斯帕滑翔机枪（Gosper Glider Gun）"。运行模拟并观察枪的行为。

2．编写readPattern()方法，从文本文件读取初始图案，并用它来设置模拟的初始条件。下面是该文件的建议格式：8 0 0 0 255 ...

图3-6 高斯帕滑翔机枪该文件的第一行定义了N，其余部分是N×N个整数（0或255），由空格隔开。你可以用Python的方法，如open和file.read来实现。这种探索有助于研究任何给定的图案在生命游戏规则下是如何演变的。添加命令行选项--pattern-file，在运行程序时使用此文件。

# 第三部分图片之乐

"你可以通过视觉观察到很多东西。"

--Yogi Berra

# 第6章 ASCII文本图形在20世纪90年代，电子邮件占据着统治地位，图形处理能力很有限，常见的做法是在电子邮件中包含一个签名，它是由文本制作的图形，一般称为ASCII文本图形（ASCII是一个简单的字符编码方案）。图6-1展示了两个例子。尽管因特网已经让共享图像容易很多，但出身卑微的文本图形还没有消失。

ASCII文本图形的源头是19世纪后期出现的打字机文本图形。在20世纪60年代，计算机有了较弱的图形处理硬件，ASCII被用于表示图形。今天，ASCII文本图形继续作为因特网上的一种表现形式，你可以在网上找到各种创意的例子。

这个项目用Python创建一个程序，从图像生成ASCII文本图形。该程序让你指定输出（文本列数）的宽度，并设置垂直比例因子。它也支持两种灰度值到ASCII字符的映射：稀疏的10级映射和更精细校正的70级映射。

要从图像生成ASCII文本图形，需要学习如何做到以下几点：

- 用Pillow将彩色图像转换成灰度图像，它是Python的图像库（PIL）的一个分支；

- 使用numpy计算灰度图像的平均亮度；

- 用一个字符串作为灰度值的快速查找表。

图6-1 ASCII文本图形的例子

## 6.1 工作原理该项目利用了这样一个事实：从远处看，我们将灰度图像看成是它们亮度的平均值。例如，在图6-2中，可以看到一个建筑物的灰度图像，在它旁边，是填充了该建筑物图像的平均亮度值的图像。如果穿过一间屋子来看这两幅图像，它们看起来相似。

ASCII文本图形的生成方法是，将图像分割成小块，并用ASCII字符替换一小块的平均RGB值。从远处看，因为眼睛的分辨率有限，我们大致会丢失细节，看到ASCII文本图形中的"平均"值，否则文本图形看起来就不那么真实。

图6-2 灰度图像的平均值该程序将给定的图像先转换为8位的灰度，让每个像素有一个灰度值，范围在[0,255]（8位整数的范围）。将这个8位值看成是亮度，0表示黑色，255表示白色，中间值是不同程度的灰色。

接着，将该图像分割成M×N个小块构成的网格（其中，M和N是ASCII文本图形中的行和列编号）。然后程序计算网格中每个小块的平均亮度值，通过预定义的一些有梯度的ASCII字符（一组不断增加的值）来表示[0,255]范围的灰度值，与适当的ASCII字符匹配。它将用这些值作为亮度值的查找表。

完成的ASCII文本图形只是一些文本行。要显示文本，就要用到Courier这样的等宽字体，因为如果每个文本字符宽度不相同，图像中字符将无法正确地按网格排列，会得到间隔不均和失真的输出。

所用字体的"横纵比"（宽度与高度之比）也会影响最终图像。如果一个字符所占空间的横纵比与该字符取代的图像小块的横纵比不同，则最终的ASCII字符图形会出现失真。实际上，你试图用一个ASCII字符来替换图像小块，所以它们的形状要匹配。例如，如果将图像分割成正方形小块，然后用一种高度拉伸的字体替换每个小块，最终的结果将出现垂直拉伸。

为了解决这个问题，需要缩放网格中的行数，以匹配Courier的长宽比。（可以向程序发送命令行参数，修改缩放，以匹配其他字体。）

总之，下面是程序生成ASCII文本图形的步骤：

1．将输入图像转成灰度；

2．将图像分成M×N个小块；

3．修正M（行数），以匹配图像和字体的横纵比；

4．计算每个小块图像的平均亮度，然后为每个小块查找合适的ASCII字符；

5．汇集各行ASCII字符串，将它们打印到文件，形成最终图像。

## 6.3 代码开始先定义灰度等级，用于生成ASCII文本图形。然后，考虑如何将图像分割成小块，以及如何计算这些小块的平均亮度。接下来，用ASCII字符替换小块，生成最终的输出。最后，为程序设置命令行解析，允许用户指定输出尺寸、输出文件名，等等。

整个项目的代码，请参阅6.4节。

### 6.3.1 定义灰度等级和网格创建程序的第一步是，先定义两种灰度等级作为全局值，用于将亮度值转换为ASCII字符。 # 70 levels of gray 1. gscale1 = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^ `". " # 10 levels of gray 2. gscale2 = "@%#*+=-:. "

1. 行的值gscale1是70级的灰度梯度，2. 行的gscale2是简单的10级灰度梯度。这两个值保存为字符串，包含一组字符串，从最黑暗变到最亮（要了解如何用字符表示灰度值的更多内容，参见Paul Bourke的《Character Representation of Grey Scale Images》，网址在http://paulbourke.net/dataformats/asciiart/）。

既然有了灰度梯度，就可以准备图像。下面的代码打开图像，并分割成网格： # open the image and convert to grayscale 1. image = Image.open(fileName).convert("L") # store the image dimensions 2. W, H = image.size[0], image.size[1] # compute the tile width 3. w = W/cols # compute the tile height based on the aspect ratio and scale of the font 4. h = w/scale # compute the number of rows to use in the final grid 5. rows = int(H/h)

在1. 行，Image.open()打开输入图像文件，Image.convert()将该图像转换为灰度图像。"L"代表luminance，是图像亮度的单位。

在2. 行，保存输入图像的宽度和高度。在3. 行，根据用户指定的列数（cols），计算小块的宽度（如果用户没有在命令行中设置其他值，程序默认使用80列）。对于3. 行的除法，使用浮点而不是整数除法，避免在计算小块尺寸时的截断误差。

知道小块的宽度后，在4. 行利用垂直比例系数（作为scale传入），计算它的高度。在5. 行，用这个网格高度来计算行数。

比例系数确定每个小块的大小，以匹配用于显示文本的字体的横纵比，这样最终图像不会失真。scale的值可以作为参数传入，或者设置为默认值0.43，在用Courier显示结果时，效果很好。

### 6.3.2 计算平均亮度接下来，计算灰度图像中每一小块的平均亮度。函数getAverageL()完成这项工作。1. def getAverageL(image): # get the image as a numpy array 2. im = np.array(image) # get the dimensions 3. w,h = im.shape # get the average 4. return np.average(im.reshape(w*h))

在1. 行，图像小块作为PIL Image对象传入。在2. 行，将image转换成一个numpy数组，此时im成为一个二维数组，包含每个像素的亮度。在3. 行，保存该图像的尺寸（宽度和高度）。在4. 行，numpy.average()计算该图像中的亮度平均值，做法是用numpy.reshape()先将维度为宽和高(w，h)的二维数组转换成扁平的一维，其长度是宽度乘以高度(w*h)。然后numpy.average()调用对这些数组值求和并计算平均值。

### 6.3.3 从图像生成ASCII内容程序的主要部分负责从图像生成ASCII内容。 # an ASCII image is a list of character strings 1. aimg = [] # generate the list of tile dimensions for j in range(rows): 2. y1 = int(j*h) y2 = int((j+1)*h) # correct the last tile if j == rows-1: y2 = H # append an empty string 3. aimg.append("") for i in range(cols): # crop the image to fit the tile 4. x1 = int(i*w) x2 = int((i+1)*w) # correct the last tile 5. if i == cols-1: x2 = W # crop the image to extract the tile into another Image object 6. img = image.crop((x1, y1, x2, y2)) # get the average luminance 7. avg = int(getAverageL(img)) # look up the ASCII character for grayscale value (avg) if moreLevels: 8. gsval = gscale1[int((avg*69)/255)] else: 9. gsval = gscale2[int((avg*9)/255)] # append the ASCII character to the string 10. aimg[j] += gsval

在程序的这一部分，ASCII图像先作为一个字符串列表保存，该列表在1. 行初始化。接下来，按计算好的图像小块行数迭代遍历，在2. 行和随后一行中，计算每个图像小块的起始和结束y坐标。虽然这些是浮点运算，但在传给图像裁剪方法之前，将它们截断为整数。

接着，因为只有当图像的宽度是列数的整数倍时，图像分割成小块时，边缘的小块才有相同的大小，所以在最后一行校正小块的y坐标，将y坐标设置为图像的实际高度。这样做确保了图像顶部的边缘不被截断。

在3. 行，为ASCII图像添加一个空字符串，作为一种紧凑的方式来表示图像的当前行。接下来会填充这个字符串（将字符串作为字符的列表）。

在4. 行和下一行，计算每个小块的左、右x坐标，在5. 行，为最后一小块校正x坐标，原因和校正y坐标时一样。在6. 行，用image.crop()提取图像小块，然后将该小块传入getAverageL()函数7. ，该函数在6.3.2节中定义，取得小块的平均亮度。在9. 行，将平均亮度值从[0，255]缩小至[0，9]（默认10级灰度梯度值的范围）。然后，用gscale2（保存的梯度字符串）作为查找表，找到对应的ASCII值。8. 行类似，不同之处在于，只有命令行标志设置为使用70级梯度时，才会用它。最后，在10. 行，在文本行中添加找到的ASCII值gsval，代码循环，直到处理完所有行。

### 6.3.4 命令行选项接下来，为程序定义一些命令行选项。这段代码使用内置的argparse类： parser = argparse.ArgumentParser(description="descStr") # add expected arguments 1. parser.add_argument('--file', dest='imgFile', required=True) 2. parser.add_argument('--scale', dest='scale', required=False) 3. parser.add_argument('--out', dest='outFile', required=False) 4. parser.add_argument('--cols', dest='cols', required=False) 5. parser.add_argument('--morelevels', dest='moreLevels', action='store_true')

在1. 行，包含指定图像文件输入的选项（唯一必须的参数），2. 行设置垂直比例因子，3. 行设置输出文件名，4. 行设置ASCII输出中的文本列数。在5. 行，添加--morelevels选项，让用户选择更多层次的灰度梯度。

### 6.3.5 将ASCII文本图形字符串写入文本文件最后，将生成的ASCII字符串列表，写入一个文本文件： # open a new text file 1. f = open(outFile, 'w') # write each string in the list to the new file 2. for row in aimg: f.write(row + '\n') # clean up 3. f.close()

在1. 行，使用内置的open()方法，打开一个新的文本文件用于写入。然后在2. 行，迭代遍历列表中的每个字符串，将它写入文件，在3. 行，关闭文件对象，释放系统资源。

## 6.5 运行ASCII文本图形生成程序要运行编写好的程序，输入类似下面这样的命令，将data/robot.jpg替换为你想使用的图像文件的相对路径。$ python ascii.py --file data/robot.jpg --cols 100

图6-3展示了ASCII文本图形，它是左侧的robot.jpg的结果。

图6-3 ascii.py的运行示例现在，你可以创建自己的ASCII文本图形了！

## 6.7 实验这里有一些想法，可以进一步探索ASCII文本图形。

1．用命令行选项--scale1.0运行该程序。生成的图像看起来如何？实验不同的scale值。将输出复制到一个文本编辑器，尝试设置不同的（固定宽度）字体，看看这样做如何影响最终图形的外观。

2．为程序添加命令行选项--invert，反转ASCII文本图形的输入值，使黑色变成白色，反之亦然（提示：在查找时用255减去小块的亮度值）。

3．在这个项目中，基于两个字符硬编码的梯度创建灰度值查找表。实现一个命令行选项，用不同的字符梯度来创建ASCII文本图形，就像这样：python3 ascii.py --map "@$%^`."

前面这样的梯度用给定的6个字符梯度，创建了一个ASCII输出，其中"@"映射到亮度值0，"."映射到亮度值255。

# 第8章三维立体画盯着图8-1看一分钟。除了随机的点，你还看到别的什么吗？图8-1是一张三维立体画，是制造三维假象的二维图像。 三维立体画通常包含一些重复的图案，仔细观察会被大脑解释为三维。如果你看不到任何图像效果，别担心。我也花了一段时间，做了一些尝试，才能看到（如果你在本书的印刷版本上看不到，请在这里尝试彩色的版本：https://github.com/electronut/pp/images/。标题的脚注提示了你应该看到的图像）。

本项目将用Python创建一张三维立体画。下面是本项目涉及的一些概念：

- 线性间距和深度知觉；

- 深度图；

- 用Pillow创建和编辑图像；

- 用Pillow绘制图像。

本项目生成的三维立体画设计为用"墙眼"方式观看。看到它们的最好方法，就是让眼睛聚焦在图像后面的点（如墙上）。有点神奇，一旦在这些图案中感知到某样东西，眼睛就会自动将它作为关注的焦点，如果三维图像已"锁定"，你很难对它视而不见的（如果你仍然无法看到图像，请看Gene Levin的文章"How to View Stereograms and Viewing Practice"[1] ，或许有帮助）。

图8-1 一张令人费解的图像，可能让你感到痛苦[2]

## 8.1 工作原理三维立体画的工作原理是改变图像中图案之间的线性间距，从而产生深度的错觉。在观看三维立体画中的重复图案时，大脑会将间距解释为深度信息，如果有多个图案和不同的间距，尤其会这样。

### 8.1.1 感知三维立体画中的深度如果你的眼睛汇聚在图像背后一个假想的点，大脑将左眼看到的一些点与右眼看到的另一些点匹配起来，你将会看到这些点位于图像之后的一个平面上。到该平面的感知距离取决于图案中的间距的数量。例如，图8-2展示了3行A。这些A每行间的距离相等，但它们的水平间距从上至下增加。

如果用"墙眼"的方式来看，图8-2中最上面一行应该出现在纸后面，中间行应该看起来像在第一行后面一点，底部一行应该出现在最远的位置。文本"floating text"应该看起来"浮在"这几行顶部。

为什么大脑将这些图案的间距解读为深度？通常情况下，如果看远处的物体，你的双眼协作，聚焦并汇聚在同一点，双眼向内转，直接指向目标点。但用"墙眼"方式观看三维立体画时，聚焦和汇聚发生在不同的位置。眼睛专注于三维立体画，但大脑将重复的模式看成来自同一个虚拟（虚构的）对象，眼睛汇聚在图像背后的一个点，如图8-3所示。解耦的聚焦和汇聚叠加在一起，让你在三维立体画中看到深度。

图8-2 线性间距和深度知觉图8-3 在三维立体画中看到深度三维立体画的感知深度取决于像素的水平间距。因为图8-2中的第一行具有最近的间隔，它出现在其他行的前面。然而，如果点的间距在图像中是变化的，大脑将认为每个点处于不同的深度，所以我们会看到一个虚拟的三维图像。

### 8.1.2 深度图

"深度图"是这样一幅图像：其中每个像素的值表示深度值，即从眼睛到该像素表示的对象部分的距离。深度图往往表现为一幅灰度图，亮的区域表示近的点，暗的区域表示远的点，如图8-4所示。

图8-4 深度图注意，鲨鱼的鼻子是图像中最亮部分，似乎最接近你。朝向尾部的较暗区域看起来最远。

因为深度图表示从每个像素中心到眼睛的深度或距离，所以可以用它来获得与图像中像素位置相关联的深度值。我们知道，在图像中，水平偏移被认为是深度。所以，如果按照对应像素值深度值的比例，来偏移（图案）图像中的像素，就会对该像素产生与深度图一致的深度知觉。如果对所有像素这样做，最终就会将整个深度图编码到图像中，生成三维立体画。

深度图的每个像素存储了深度值，并且该值的分辨率取决于表示它的位数。因为本章采用常见的8位图像，深度值的范围是[0,255]。

顺便说一下，图8-4中的图像就是用于创建图8-1中的三维立体画的深度图。你很快就能学会自己如何做到这一点。

该项目的代码将遵循以下步骤：

1．读入深度图；

2．读入一幅平铺图像或创建一个"随机点"平铺图像；

3．通过重复平铺图像创建一幅新图像。该图像的尺寸与深度图一致；

4．对新图像中的每个像素，根据该像素相关联的深度值，将它按比例地向右移；

5．将三维立体画写入一个文件。

## 8.3 代码为了从输入的深度图生成三维立体画，首先重复一幅给定的平铺图像，生成一幅中间图像。接下来，生成一幅充满随机点的平铺图像。然后进入生成三维立体画的核心代码，即利用所提供的深度图中的信息，移动输入的图像。要查看完整的项目，请直接跳到8.4节。

### 8.3.1 重复给定的平铺图像我们从利用createTiledImage()方法开始，通过平铺一个图形文件，创建一幅新的图像。图像尺寸由dims元组指定，该元组形式为（width, height）。

# tile a graphics file to create an intermediate image of a set size def createTiledImage(tile, dims): # create the new image 1. img = Image.new('RGB', dims) W, H = dims w, h = tile.size # calculate the number of tiles needed 2. cols = int(W/w) + 1 3. rows = int(H/h) + 1 # paste the tiles into the image for i in range(rows): for j in range(cols): 4. img.paste(tile, (j*w, i*h)) # output the image return img

在1. 行，利用提供的尺寸（dims）创建新的Python图像库（PIL）Image对象。新图像的尺寸由元组dims给出，形式是（width, height）。接着，保存平铺图像和输出文件的宽度和高度。在2. 行，确定列数，在3. 行，确定中间图像所需的行数，方法是用最终图像的尺寸除以平铺图像的尺寸。除的结果每次加1，如果输出图像的尺寸不是正好是平铺图像的整数倍，这也能确保右边最后的平铺图像不会缺失。如果没有这种预防措施，图像的右边可能被切断。然后，在4. 行，循环遍历行和列，并用平铺图像填充它们。通过乘积(j*w, i*h)，确定平铺图像左上角的位置，这样它能对准行和列。完成后，该方法返回指定尺寸的Image对象，用输入图像tile平铺。

### 8.3.2 从随机圆创建平铺图像如果用户不提供平铺图像，就利用createRandomTile()方法，用随机圆圈创建一张平铺图像。

# create an image tile filled with random circles def createRandomTile(dims): # create image 1. img = Image.new('RGB', dims) 2. draw = ImageDraw.Draw(img) # set the radius of a random circle to 1% of # width or height, whichever is smaller 3. r = int(min(*dims)/100) # number of circles 4. n = 1000 # draw random circles for i in range(n): # -r makes sure that the circles stay inside and aren't cut off # at the edges of the image so that they'll look better when tiled 5. x, y = random.randint(0, dims[0]-r), random.randint(0, dims[1]-r) 6. fill = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) 7. draw.ellipse((x-r, y-r, x+r, y+r), fill) return img

在1. 行，用dim给出的尺寸创建新的Image对象。用ImageDraw.Draw() 2. 在该图像中画圆圈，用宽或高中较小值的1/100作为半径，画圆圈3. （Python的*运算符将dim元组中的宽度和高度值解包，这样就能传入到min()方法中）。

在4. 行，设置要画的圆圈数为1000。然后调用random.randint()，获得范围为[0, width-r]和[0, height-r]的两个随机整数，从而算出每个圆圈的x和y坐标5. 。"-r"确保生成的圆圈保持在width×height的图像矩形内部。不带-r，画的圆圈可能就在图像边缘，这意味着它会被切掉一部分。如果平铺这样的图像来创建三维立体画，结果不会好看，因为两个平铺图像之间没有空间。

要生成一个随机圆圈，先画出轮廓，然后填充颜色。在6. 行，在[0,255]的范围内随机选取RGB值，用选择颜色填充。最后，在7. 行，用draw中的ellipse()方法绘制每个圆圈。该方法的第一个参数是圆的边界矩形，它由左上角和右下角指定，分别为(x-r, y-r)和(x+r, y+r)，其中(x, y)是该圆的圆心，r是半径。

让我们在Python解释器中测试这种方法。>>> import autos >>> img = autos.createRandomTile((256, 256)) >>> img.save('out.png') >>> exit()

图8-5展示了测试的输出。

图8-5 尝试运行createRandomTile()

正如你在图8-5中看到的，我们已经创建了随机点的平铺图像。可以使用它来创建的三维立体画。

### 8.3.3 创建三维立体画现在，让我们创建一些三维立体画。createAutostereogram()方法完成了大部分工作，如下所示：def createAutostereogram(dmap, tile): # convert the depth map to a single channel if needed 1. if dmap.mode is not 'L': dmap = dmap.convert('L') # if no image is specified for a tile, create a random circles tile 2. if not tile: tile = createRandomTile((100, 100)) # create an image by tiling 3. img = createTiledImage(tile, dmap.size) # create a shifted image using depth map values 4. sImg = img.copy() # get access to image pixels by loading the Image object first 5. pixD = dmap.load() pixS = sImg.load() # shift pixels horizontally based on depth map 6. cols, rows = sImg.size for j in range(rows): for i in range(cols): 7. xshift = pixD[i, j]/10 8. xpos = i - tile.size[0] + xshift 9. if xpos > 0 and xpos < cols: 10. pixS[i, j] = pixS[xpos, j] # display the shifted image return sImg

在1. 行，进行完整性检查，确保深度图和图像具有相同的尺寸。在2. 行，如果用户没有提供平铺图像，就创建随机圆圈平铺图像。在3. 行，创建一张平铺好的图像，符合提供的深度图的大小。然后，在4. 行生成这张平铺好的图像的副本。

在5. 行，调用Image.load()方法，将图像数据加载到内存中。该方法允许用形如[i, j]的二维数组来访问图像像素。在6. 行，将图像的尺寸保存为行数和列数，将图像看成单个像素构成的网格。

三维立体画创建算法的核心在于，根据从深度图中收集的信息，移动平铺图像中像素的方式。要做到这一点，遍历平铺图像，处理每一个像素。在7. 行，根据深度图pixD中的相关像素，查找偏移的值。然后将这个深度值除以10，因为这里用的是8位深度图，这意味着深度的范围是0到255。如果除以10，得到的深度值范围是0到25。由于深度图输入图像的尺寸通常是几百像素，所以这些偏移值很合适（尝试改变除数，看看它如何影响最终图像）。

在8. 行，计算像素的新x位置，用平铺图像填充三维立体画。每隔w个像素，像素的值不断重复，由公式ai = ai + w表示，其中的ai 是在x轴下标i 处的给定像素的颜色（因为考虑的是像素行，而不是列，所以忽略y方向）。

要创建深度感，就要让间隔（或重复的间距）与该像素的深度图值成正比。这样在最终的三维立体画图像中，每个像素和它前一次（周期地）出现相比，偏移了delta_i。这可以表示为bi =bi-w+δt

这里，bi 表示最后的三维立体画图像中，下标i 处给定像素的颜色值。这正是8. 行所做的事。深度图值为0（黑色）的像素没有偏移，被视为背景。

在10. 行，用偏移的值替换每个像素。在9. 行，检查确保没有试图访问不在图像中的像素，因为偏移，在图像边缘可能发生这种情况。

### 8.3.4 命令行选项现在，我们来看看该程序的main()方法，其中提供了一些命令行选项。 # create a parser parser = argparse.ArgumentParser(description="Autosterograms...") # add expected arguments 1. parser.add_argument('--depth', dest='dmFile', required=True) parser.add_argument('--tile', dest='tileFile', required=False) parser.add_argument('--out', dest='outFile', required=False) # parse args args = parser.parse_args() # set the output file outFile = 'as.png' if args.outFile: outFile = args.outFile # set tile tileFile = False if args.tileFile: tileFile = Image.open(args.tileFile)

在1. 行，像以前的项目一样，利用argparse为程序定义了一些命令行选项。一个必需的参数是深度图文件，两个可选的参数是平铺图像文件名和输出文件名。如果未指定平铺图像，程序会生成随机圆圈平铺图像。如果未指定输出文件名，则三维立体画会输出到as.png文件。

## 8.5 运行三维立体画生成程序现在，我们用凳子（stool-depth.png）的深度图运行该程序。$ python3 autos.py --depth data/stool-depth.png

图8-6左边展示了深度图，右边展示了生成的三维立体画。因为没有为平铺提供图像，这张三维立体画使用了随机生成的平铺图像。

图8-6 autos.py运行示例现在，让我们给定一个平铺图像作为输入。像前面一样使用stool-depth.png深度图，但这一次，提供图像escher-tile.jpg[3] 作为平铺图像。$ python3 autos.py --depth data/stool-depth.png -tile data/escher-tile.jpg

图8-7展示了输出。

图8-7 使用平铺图像的autos.py运行示例

## 8.7 实验这里有一些方法，可以进一步探索三维立体画。

1．编程创建类似图8-2的图像，演示图像中线性间距的变化如何制造深度的幻觉（提示：利用图像平铺和Image.paste()方法）。

2．为程序添加一个命令行选项，指定应用于深度图值的比例（回忆一下，代码中深度图值除以10）。变更如何影响到三维立体画？

3．学习用SketchUp这样的工具，创建自己的三维模型深度图（http://sketchup. com/），或在线访问许多现成的SketchUp模型。利用SketchUp的Fog选项来创建你的深度图。如需帮助，看看这个YouTube视频：https://www.youtube.com/watch?v= fDzNJYi6Bok/。

[1] http://colorstereo.com/texts_.txt/practice.htm

[2] 隐藏图像是鲨鱼。

[3] http://calculus-geometry.hubpages.com/hub/Free-M-C-Escher-Tessellation-Background-Patterns-Tiling-Lizard-Background/

# 第四部分走进三维

"在一维中，移动一个点难道不是产生了有两个端点的线段？

在两维中，移动一段线难道不是产生了有四个端点的正方形？

在三维中，移动一个正方形难道不是产生了（我的眼睛没有看见）

那种神奇的造物，立方体，有八个端点？"

--Edwin A. Abbott, Flatland: A Romance of Many Dimensions

# 第10章粒子系统在计算机图形世界中，粒子系统是用许多小图元（如点、线、三角形和多边形）来表示的物体，如烟雾、火焰，甚至头发，没有明确的几何形状，因此很难用标准技术来建模。

例如，如何在计算机上制造一次爆炸效果？设想爆炸从空间中的一个点开始，然后向外扩张，作为一个快速扩大的、复杂的三维实体，随时间而改变形状和颜色。不夸张地说，尝试建立数学模型就令人望而生畏。

但现在设想一下，爆炸包含一群细小的粒子，每个粒子有关联的位置和颜色。爆炸开始时，粒子在空间中的一个点上聚成一图。随着时间的推移，它们根据一定的数学规则向外移动，并改变颜色，让你定期绘制所有粒子，从而生成爆炸的动画。利用好的数学模型、大量粒子，以及透明度和公告板（billboarding）这样的渲染技术，可以创建逼真的效果，如图10-1所示。

本项目会制定粒子运动的数学模型，将它表示为时间的函数，并利用图形处理单元（GPU）的着色器进行计算。然后，会设计一种渲染方案，利用一种名为公告板的技术，它让二维图像一直面向观众，从而使二维图像看起来像是三维的，用一种令人信服的方式来绘制这些粒子。还会用OpenGL着色器让粒子旋转，并生成动画场景。你可以通过按键来打开或关闭各种效果，进行比较。

图10-1 已完成项目的运行示例数学模型将设置每个粒子的初始位置和速度，并决定粒子如何随时间运动。你可以让每个纹理的黑色区域透明，利用正方形图像创建火花，保持每个火花面向观众，使它们看起来有立体感。你会生成粒子的动画，定期更新它们的位置，其亮度随着时间的推移逐渐减弱。

下面是将要探索的一些概念：

- 制定喷泉粒子系统的数学模型；

- 利用GPU着色器计算；

- 利用纹理和公告板模拟复杂的三维对象；

- 利用OpenGL渲染功能，如混合、深度遮掩和Alpha通道，绘制半透明物体；

- 利用相机模型绘制三维透视图。

## 10.1 工作原理要创建动画，就需要一个数学模型。从一个固定点开始，移动一些粒子，随时间推移沿抛物线轨迹运动，形成火花喷泉，如图10-2所示。这就是喷泉粒子系统。

图10-2 5个示例火花在喷泉粒子系统中的轨迹我们的粒子系统应具有以下特性：

- 粒子应该从固定点的出现，它们的运动轨迹应该是抛物线；

- 粒子应该能相对于喷泉的垂直轴（z轴或高度），运动预定距离；

- 较接近喷泉垂直轴中心的粒子，应该比离中心较远的粒子初速度更大；

- 要产生更逼真的效果，粒子不应全部同时喷射；

- 粒子的亮度应该随时间推移逐渐淡出。

### 10.1.1 为粒子运动建模假设粒子系统包含N个粒子。第i 个粒子的运动方程如下：

这里，Pt 是在时间t 的位置。P0 为粒子的初始位置，V0 是粒子的初始速度，a 是加速度。可以认为a是系统中的重力加速度，让粒子沿向下的弧线运动。

这些参数都是三维向量，可以表示为三维坐标。例如，使用加速度值是（0，0，-9.8），这是地球在z 轴（垂直）方向的重力加速度，单位是米每平方秒。

### 10.1.2 设置最大范围要让喷泉看起来逼真，粒子应相对于圆锥体的z 轴，以不同的角度飞出。但也要设置一个最大范围，让每个粒子的初始速度在一定范围内，让这些粒子呈漏斗状，形成喷泉的样子。为了实现这个目标，将速度与垂直轴的最大角度确定为20度，如图10-3所示。

图10-3 限制每个粒子的初始速度范围。每个粒子分配的速度在阴影圆内在图10-3中，方位角φ 是速度向量与x 轴的夹角。倾斜角θ 是速度向量与z 轴的夹角。倾斜角的选择范围让速度向量处于图中浅灰色阴影区域内。

速度方向应该从大圆圈包围的半球部分中随机选择。这些方向的端点处于一个单位半径的球面上，这样就可以用球坐标系来计算它们。此外，我们希望速度值随着与轴的夹角增大而减小。考虑到这一点，粒子的初始速度如下：

这里，α 是粒子的倾斜角与最大角度（这个例子中是20度）之比。因此，随着这个比值逐渐变为1.0，速度（二次地）下降。速度V 是单位球面上一个点，像下面这样：

在[0，20]度范围内随机选择一个倾斜角，在[0，360]度范围内随机选择一个方位角：

这个方程让粒子指向图10-3中圆圈区域内的一个随机点（注意，在这个程序中，所有角度计算需要用弧度，不是度）。

我们也希望确保粒子不在同一时间开始（原因请参阅10.10节）。要做到这一点，为每个粒子计算一个时间延迟，稍后在计算粒子位置时使用。第i 个粒子的延迟计算如下：

这些方程中随意采用的数值常数是怎么来的？例如，为什么用0.05作为延迟时间，用20度作为最大角度？答案是实验。重要的是创建一个基本模型，然后调整这些常数，以获得最佳视觉效果。改变程序中的这些参数，看看不同的值如何影响结果。

### 10.1.3 渲染粒子渲染粒子的一种简单方式，就是将它们绘制为点。OpenGL有GL_POINTS图元，本质上是屏幕上的一个点；你可以控制点的像素大小和颜色。但我们希望粒子看起来像小火花，并且随着喷发而旋转。

从头开始绘制火花太复杂了，所以需要一张火花的照片，作为纹理粘贴到一个矩形（也称为"四边形"）。喷泉中的每个粒子都被绘制成火花的三角形纹理图像。但是，这提出两个问题。首先，不希望正方形火花，因为那显得很假。其次，如果从其他角度看喷泉，四边形的方向会不对。

### 10.1.4 利用OpenGL混合来创建更逼真火花为了创造更逼真的火花，我们利用OpenGL的混合（blending）。结合传入的片段（片段着色器执行之后）和帧缓冲区中已有的内容。这项操作通常涉及Alpha通道。

例如，假设在屏幕上绘制两个多边形，并想将它们混合在一起。你可以用alpha混合的技巧，它的工作原理是将两个透明片重叠起来。alpha通道表示像素的不透明度，它是透明程度的量度。除了表示一个像素颜色的红、绿、蓝分量之外，还可以存储一个alpha值，得到的颜色方案称为RGBA。对于32位的RGBA颜色方案，alpha值的范围是[0,255]，0是完全透明，255是完全不透明。alpha通道本身不做任何事情。只有用alpha值来改变像素的最终RGB值时，才会创建各种透明效果。

OpenGL提供了几种方法来定制混合方程。对于喷泉粒子，我们将使用图10-4所示的纹理，但要让纹理的黑色区域消失，这样就会只看到火花。

启用OpenGL的混合，用片段的alpha值乘以纹理的颜色，可以让黑色区域消失。对于黑色区域，RGB颜色值是（0，0，0），如果乘以alpha值，将得到0。因此，经过混合，黑色区域在最终图像中的不透明度是0，你看到的只是背景颜色，实际上去掉了火花纹理的黑色区域（alpha值在片段着色器中设置，在10.3.5节中有介绍）。

图10-4 火花纹理，标有RGB值（0，0，0）为黑色，（255，255，255）为白色注意除了在着色器中设置alpha值，也可以利用纹理图像中的alpha通道，为黑色和白色区域设定不同的alpha值，从而控制透明度。在着色器中使用alpha值，创建带有黑色背景的纹理，再让所有黑色区域透明，这更简单，优于在纹理中使用alpha通道，让特定区域有不同的透明度值。

### 10.1.5 使用公告板对于第二个问题（如果从其他角度看喷泉，四边形的方向不对），我们将使用公告板。我们不是绘制复杂的三维物体，而是放置一个二维的图片，让你总是看到其正面（面向观看的方向），作为一种公告板。例如，在开发三维游戏时，背景是树木景观，可以用一个带纹理的多边形公告板来替代树木景观。只要玩家靠得不太近，假的"图片树"看起来就很逼真。

现在来看看放置多边形背后的数学，以便让它总是面向观看的方向。图10-5展示了如何将一个纹理四边形变成一个公告板。

图10-5 公告板对准是相对于四边形上的定位点来说的。在这个例子中，会选择四边形的中心。要对准四边形，需要三个正交向量，创建一个小坐标系统。我们感兴趣的第一个向量是n ，代表四边形的法线向量。法线向量垂直于四边形所在的平面，这意味着设定的法线向量方向，就是四边形面向的方向。我们希望四边形面向观看的方向，即v ，所以n 向量需要对准该向量，但方向相反。因为观看的方向朝向屏幕，所以四边形的法线向量应该指向相反的方向：从屏幕向外。

这意味着我们希望方向n = -v 。现在，选择一个向量u ，这是四边形最终位置的近似向上向量。选择u 为（0，0，1），因为z方向指"向上"（说这个向量是近似的，是因为虽然我们事先知道四边形的法线向量，但不知道摄像头的方向）。然后计算第三个向量r ，这里r = u ×n （两个向量的叉积）。现在有了两个正交向量，n 和r ，都在四边形的平面中。叉积这两个向量，得到一个新向量。因此，得到了新的向上向量u ' = n ×r =n × (u ×n )。我们需要一个新的向上向量，以确保这3个向量是正交的，或彼此垂直。最后，在计算过程中，这些向量都需要归一化，让长度等于一个单位，从而创建一个正交坐标系（其中所有向量是单位长度并且正交）。有了这3个向量，就可以根据三维图形理论，用一个旋转矩阵进行任意方向的旋转。旋转矩阵R 将位于原点的正交坐标系统旋转到r 、u ' 和n 构成的坐标系统：

应用这个旋转矩阵，将带纹理的四边形正确地对准观看的方向，使其成为一个公告板。

### 10.1.6 生成火花动画要生成火花喷泉的动画，就要利用GLFW库，通过更新渲染和时间，定时绘制粒子系统的各个位置。

## 10.3 粒子系统的代码我们开始先定义喷泉中使用的粒子的三维几何形状。然后，再看看如何创建动画中粒子之间的时间延迟，如何为粒子设置初始速度，以及如何在程序中使用OpenGL的顶点和片段着色器。最后，看看如何将所有这些整合起来，渲染粒子系统。整个项目的代码，请直接跳到10.4节。

喷泉的代码封装在一个类中，名为ParticleSystem，它创建了粒子系统，建立了OpenGL着色器，用OpenGL渲染系统，每隔五秒钟重新开始动画。

### 10.3.1 定义粒子的几何形状首先，创建一个顶点数组对象（VBO）来管理后续的顶点属性数组，从而定义这些粒子的几何形状。 # create Vertex Array Object (VAO) self.vao = glGenVertexArrays(1) # bind VAO glBindVertexArray(self.vao)

每个粒子是一个正方形，其顶点和纹理坐标定义如下： # vertices s = 0.2 1. quadV = [ -s, s, 0.0, -s, -s, 0.0, s, s, 0.0, s, -s, 0.0, s, s, 0.0, -s, -s, 0.0 ] 2. vertexData = numpy.array(numP*quadV, numpy.float32) 3. self.vertexBuffer = glGenBuffers(1) 4. glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer) 5. glBufferData(GL_ARRAY_BUFFER, 4*len(vertexData), vertexData, GL_STATIC_DRAW) # texture coordinates 6. quadT = [ 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0 ] tcData = numpy.array(numP*quadT, numpy.float32) self.tcBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.tcBuffer) glBufferData(GL_ARRAY_BUFFER, 4*len(tcData), tcData, GL_STATIC_DRAW)

在1. 行，定义了正方形的顶点，各边以原点为中心，长度为0.4。对于两个GL_TRIANGLES，顶点的排序是相同的。然后，在2. 行，将这些顶点重复numP次，创建一个numpy数组：每个四边形表示系统中的一个粒子（所有要绘制的几何图形都放入到一个大数组）。

接下来，将这些顶点放入一个顶点缓冲区对象，就像在第9章中所做的一样。在3. 行创建VBO，在4. 行绑定。然后在5. 行，用顶点数据填充绑定的缓冲区。代码4 * len(vertexData)指明在vertexData数组中，每个元素需要4个字节。

最后，在6. 行定义四边形的纹理坐标，随后几行代码设置了相关的VBO。

### 10.3.2 为粒子定义时间延迟数组接下来，为粒子定义时间延迟数组。我们希望每组四个顶点的时间延迟一样，这代表一个正方形的粒子，如以下代码所示： # time lags 1. timeData = numpy.repeat(0.005*numpy.arange(numP, dtype=numpy.float32), 4) self.timeBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.timeBuffer) glBufferData(GL_ARRAY_BUFFER, 4*len(timeData), timeData, GL_STATIC_DRAW)

在1. 行，numpy.arange()创建了一个数组，包含不断增加的值，即[0，1，...，numP-1]。将这个数组乘以0.005，用参数4调用numpy.repeat()，产生一个数组，即[0.0，0.0，0.0，0.0，0.005，0.005，0.005，0.005，...]。接下来的代码设置了VBO。

### 10.3.3 设置粒子初始速度接下来生成粒子的初始速度。我们的目标是生成一些随机的速度，它们与垂直轴的夹角不超过某个最大值。下面是代码： # velocites velocities = [] # cone angle 1. coneAngle = math.radians(20.0) # set up particle velocities for i in range(numP): # inclination 2. angleRatio = random.random() a = angleRatio*coneAngle # azimuth 3. t = random.random()*(2.0*math.pi) # get velocity on sphere 4. vx = math.sin(a)*math.cos(t) vy = math.sin(a)*math.sin(t) vz = math.cos(a) # speed decreases with angle 5. speed = 15.0*(1.0 - angleRatio*angleRatio) # add a set of calculated velocities 6. velocities += 6*[speed*vx, speed*vy, speed*vz] # set up velocity vertex buffer self.velBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.velBuffer) 7. velData = numpy.array(velocities, numpy.float32) glBufferData(GL_ARRAY_BUFFER, 4*len(velData), velData, GL_STATIC_DRAW)

在1. 行，定义了限制喷泉粒子轨迹的锥角。（注意，用内置math.radians()方法，将角度转换为弧度。）接下来，用10.1.1节中讨论的公式，计算每个粒子的速度。

在2. 行，生成一个随机分数，后面一行用它乘以最大倾斜角，来计算当前倾斜角。接着，在3. 行生成方位角，因为random.random()返回值在[0，1]之间，所以用该值乘以2.0 * math.pi，得到0至2的一个随机弧度。

从4. 行开始，利用球坐标公式，计算单位球面上的速度向量。在5. 行，用2. 行得到的角度比算出一个速度，它与垂直角度成反比。在 6. 行，计算粒子的最终速度，并针对两个三角形的所有6个顶点，重复这个值。在7. 行，利用Python列表创建一个numpy的数组，这就可以为这些速度创建一个VBO了。最后，启用所有的顶点属性，并为顶点缓冲区设置数据格式（因为这个过程类似于第9章，这里略过，直接讨论顶点着色器）。

### 10.3.4 创建顶点着色器顶点着色器处理各个顶点，从而计算粒子系统的轨迹。下面是它的代码：

#version 330 core in vec3 aVel; in vec3 aVert; in float aTime0; in vec2 aTexCoord; uniform mat4 uMVMatrix; uniform mat4 uPMatrix; uniform mat4 bMatrix; uniform float uTime; uniform float uLifeTime; uniform vec4 uColor; uniform vec3 uPos; out vec4 vCol; out vec2 vTexCoord;

顶点着色器对四边形的每个顶点执行，对粒子系统中的所有四边形。它首先定义属性数组中的一些变量，它代表要传入VBO的数组。然后定义一些uniform变量，它们在执行着色器时保持不变。最后定义out数量，它们在顶点着色器中设置，并传递给片段着色器进行插值。

现在，来看看着色器的main()函数：void main() { // set position 1. float dt = uTime - aTime0; 2. float alpha = clamp(1.0 - 2.0*dt/uLifeTime, 0.0, 1.0); 3. if(dt < 0.0 || dt > uLifeTime || alpha < 0.01) { // out of sight! gl_Position = vec4(0.0, 0.0, -1000.0, 1.0); } else { // calculate new position 4. vec3 accel = vec3(0.0, 0.0, -9.8); // apply a twist float PI = 3.14159265358979323846264; 5. float theta = mod(100.0*length(aVel)*dt, 360.0)*PI/180.0; 6. mat4 rot = mat4(vec4(cos(theta), sin(theta), 0.0, 0.0), vec4(-sin(theta), cos(theta), 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0)); // apply billboard matrix 7. vec4 pos2 = bMatrix*rot*vec4(aVert, 1.0); // calculate position 8. vec3 newPos = pos2.xyz + uPos + aVel*dt + 0.5*accel*dt*dt; // apply transformations 9. gl_Position = uPMatrix * uMVMatrix * vec4(newPos, 1.0); } // set color 10. vCol = vec4(uColor.rgb, alpha); // set texture coordinates vTexCoord = aTexCoord; }

在1. 行，针对特定的粒子计算当前经过的时间，这是当前时间步骤与该粒子的延迟时间之间的差。然后在2. 行为顶点计算alpha值，该值随着时间的流逝而减小，让粒子逐渐淡出。利用GLSL中的clamp()，将值限制在范围[0，1]之内。

为了在粒子生命周期结束时让粒子消失，将它们放在OpenGL的视锥之外，这样它们会被裁剪掉。在3. 行，检查粒子的生命周期是否结束（根据粒子系统构造函数中的设置），或者其alpha值低于特定值，这时将最终位置设置到视锥之外。

在4. 行，设置粒子加速度为9.8米/秒2 ，即由于地球引力而产生的加速度。当粒子以较高的初始速度飞出喷泉时，为了让它们快速旋转，使用mod()方法（类似于Python的取模运算%），在5. 行，将角度值限制在范围[0，360]之内。在6. 行，利用这个计算出的角度，绕四边形的z 轴旋转，根据绕z 轴旋转角度的变换矩阵公式，像下面这样：

在7. 行，对粒子的顶点应用两个转换：刚刚计算出的旋转和用bMatrix的公告板旋转。在8. 行，利用前面讨论的运动方程，计算顶点的当前位置（该行中的uPos只是让你任意指定喷泉原点的位置）。

在9. 行，对粒子位置应用模型视图和投影矩阵。最后，在10. 行和下一行中，设置的颜色和纹理坐标，传入片段着色器用于插值（请注意，在2. 行基于计算设置顶点的alpha值）。

### 10.3.5 创建片段着色器现在，来看看片段着色器，它设置像素的颜色。

#version 330 core uniform sampler2D uSampler; in vec4 vCol; in vec2 vTexCoord; out vec4 fragColor; void main() { // get the texture color 1. vec4 texCol = texture2D(uSampler, vec2(vTexCoord.s, vTexCoord.t)); // multiply texture color by set vertex color; use the vertex color alpha 2. fragColor = vec4(texCol.rgb*vCol.rgb, vCol.a); }

在1. 行，用GLSL的texture2D()方法，利用从顶点着色器传入的纹理坐标，为火花图像查找基础纹理颜色（从用作纹理的图像中查找的颜色）。然后，将这个纹理颜色值乘以火花喷泉的颜色，并将得到的颜色设置给输出变量fragColor2. 。喷泉的颜色是在每个粒子系统重新启动时，由ParticleSystem的restart()方法随机设置的。alpha值是根据顶点着色器中的计算来设置的，并在渲染时用于混合。

### 10.3.6 渲染代码按照以下步骤来渲染喷泉粒子系统：

1．启用顶点/片断程序；

2．设置模型视图和投影矩阵；

3．基于当前摄像机的观看方向，计算并设置公告板矩阵；

4．针对位置、时间、生命周期和颜色，设置uniform变量；

5．针对顶点、纹理坐标、时间延迟和速度，设置顶点属性数组；

6．启用纹理并绑定到粒子火花纹理；

7．禁用深度缓冲写入；

8．启用OpenGL的混合；

9．绘制几何图形。

让我们来看看实现其中一些步骤的代码片段。计算公告板的旋转矩阵这段代码计算公告板的旋转矩阵： N = camera.eye - camera.center 1. N /= numpy.linalg.norm(N) U = camera.up U /= numpy.linalg.norm(U) R = numpy.cross(U, N) U2 = numpy.cross(N, R) 2. bMatrix = numpy.array([R[0], U2[0], N[0], 0.0, R[1], U2[1], N[1], 0.0, R[2], U2[2], N[2], 0.0, 0.0, 0.0, 0.0, 1.0], numpy.float32) 3. glUniformMatrix4fv(self.bMatrixU, 1, GL_TRUE, bMatrix)

你已经看到了构造一个旋转矩阵背后的理论，该矩阵让四边形保持为"公告板"，即对准观看方向（这是必需的，以便让喷泉粒子总是面对观察的方向）。在1. 行，用numpy.linalg.norm()对向量规一化（这使得向量的大小等于1）。在2. 行，将旋转矩阵组装为一个numpy数组，然后在3. 行将它放入程序中。主要的渲染代码主要的渲染代码用alpha混合，让粒子系统有透明性。这种技术在OpenGL中常用于渲染半透明物体。 # enable texture 1. glActiveTexture(GL_TEXTURE0) 2. glBindTexture(GL_TEXTURE_2D, self.texid) 3. glUniform1i(self.samplerU, 0) # turn depth mask off if self.disableDepthMask: 4. glDepthMask(GL_FALSE) # enable blending if self.enableBlend: 5. glBlendFunc(GL_SRC_ALPHA, GL_ONE) 6. glEnable(GL_BLEND) # bind VAO 7. glBindVertexArray(self.vao) # draw 8. glDrawArrays(GL_TRIANGLES, 0, 6*self.numP)

在1. 行，激活第一个OpenGL纹理单元（GL_TEXTURE0）。我们只有一个纹理单元，但由于在OpenGL上下文中，同一时间可以激活多个纹理单元，所以针对每个纹理单元显式调用是良好的编程习惯。在2. 行，激活纹理对象，它是在ParticalSystem的构造函数中，利用glutils.loadTexture()和火花图像创建的。

纹理利用采样在着色器中访问，在3. 行，设置采样变量使用第一个纹理单元GL_TEXTURE0。然后，利用OpenGL混合切除纹理中的黑色像素，但这些"看不见"的像素仍然具有关联的深度值，可以掩盖那些在它们后面的、其他粒子的某些部分。为了避免这种情况，在4. 行禁用深度缓存写入。

注意严格来说，这是错误的绘制方式，因为如果混合这些半透明的物体和不透明的物体，它们的深度测试就不正确。渲染这样的场景，正确的做法应该是先绘制不透明的物体，然后启用混合，按深度从后到前对半透明物体排序，最后绘制它们。但是，因为有这么多运动的粒子，这个简单的近似是可以接受的，而且最后，它看起来不错，而这才是你关心的。

在5. 行，设置OpenGL混合功能，以便使用从片段着色器传入的源像素的alpha值，在6. 行，启用OpenGL混合。然后，在7. 行绑定到创建的VAO，这启用了你建立的所有的顶点属性，在8. 行，在屏幕上绘制绑定的顶点缓冲区对象。

### 10.3.7 Camera类最后，Camera类设置了OpenGL的观看参数：

# a simple camera class class Camera: """helper class for viewing""" 1. def __init__(self, eye, center, up): self.r = 10.0 self.theta = 0 self.eye = numpy.array(eye, numpy.float32) self.center = numpy.array(center, numpy.float32) self.up = numpy.array(up, numpy.float32) def rotate(self): """rotate eye by one step""" 2. self.theta = (self.theta + 1) % 360 # recalculate eye 3. self.eye = self.center + numpy.array([ self.r*math.cos(math.radians(self.theta)), self.r*math.sin(math.radians(self.theta)), 0.0], numpy.float32)

三维立体图的特征通常在于3个参数：眼睛位置、向上向量和方向向量。Camera类包含这些参数，并提供了一种便捷的方式，在每一个时间步骤旋转。

在1. 行的构造函数设置了camera对象的初始值。调用rotate()方法时，增加旋转角度2. ，并计算旋转后新的眼睛位置和方向3. 。

注意点(r cos(θ ), r sin(θ ))表示一个点，它在以原点为中心、半径为r 的圆上，θ 是该点到原点的连线与x 轴的夹角。转换中使用了center，确保即使旋转中心不在原点，也能工作。

## 10.4 粒子系统完整代码这是粒子系统的完整代码。也可以在https://github.com/electronut/pp/tree/master/ particle-system/ps.py找到它。import sys, random, math import OpenGL from OpenGL.GL import * import numpy import glutils strVS = """ #version 330 core in vec3 aVel; in vec3 aVert; in float aTime0; in vec2 aTexCoord; uniform mat4 uMVMatrix; uniform mat4 uPMatrix; uniform mat4 bMatrix; uniform float uTime; uniform float uLifeTime; uniform vec4 uColor; uniform vec3 uPos; out vec4 vCol; out vec2 vTexCoord; void main() { // set position float dt = uTime - aTime0; float alpha = clamp(1.0 - 2.0*dt/uLifeTime, 0.0, 1.0); if(dt < 0.0 || dt > uLifeTime || alpha < 0.01) { // out of sight! gl_Position = vec4(0.0, 0.0, -1000.0, 1.0); } else { // calculate new position vec3 accel = vec3(0.0, 0.0, -9.8); // apply a twist float PI = 3.14159265358979323846264; float theta = mod(100.0*length(aVel)*dt, 360.0)*PI/180.0; mat4 rot = mat4(vec4(cos(theta), sin(theta), 0.0, 0.0), vec4(-sin(theta), cos(theta), 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0)); // apply billboard matrix vec4 pos2 = bMatrix*rot*vec4(aVert, 1.0); // calculate position vec3 newPos = pos2.xyz + uPos + aVel*dt + 0.5*accel*dt*dt; // apply transformations gl_Position = uPMatrix * uMVMatrix * vec4(newPos, 1.0); } // set color vCol = vec4(uColor.rgb, alpha); // set tex coords vTexCoord = aTexCoord; } """ strFS = """ #version 330 core uniform sampler2D uSampler; in vec4 vCol; in vec2 vTexCoord; out vec4 fragColor; void main() { // get texture color vec4 texCol = texture(uSampler, vec2(vTexCoord.s, vTexCoord.t)); // multiply by set vertex color; use the vertex color alpha fragColor = vec4(texCol.rgb*vCol.rgb, vCol.a); } """ # a simple camera class class Camera: """helper class for viewing""" def __init__(self, eye, center, up): self.r = 10.0 self.theta = 0 self.eye = numpy.array(eye, numpy.float32) self.center = numpy.array(center, numpy.float32) self.up = numpy.array(up, numpy.float32) def rotate(self): """rotate eye by one step""" self.theta = (self.theta + 1) % 360 # recalculate eye self.eye = self.center + numpy.array([ self.r*math.cos(math.radians(self.theta)), self.r*math.sin(math.radians(self.theta)), 0.0], numpy.float32) # particle system class class ParticleSystem: # initialization def __init__(self, numP): # number of particles self.numP = numP # time variable self.t = 0.0 self.lifeTime = 5.0 self.startPos = numpy.array([0.0, 0.0, 0.5]) # load texture self.texid = glutils.loadTexture('star.png') # create shader self.program = glutils.loadShaders(strVS, strFS) glUseProgram(self.program) # set sampler texLoc = glGetUniformLocation(self.program, b"uTex") glUniform1i(texLoc, 0) # uniforms self.timeU = glGetUniformLocation(self.program, b"uTime") self.lifeTimeU = glGetUniformLocation(self.program, b"uLifeTime") self.pMatrixUniform = glGetUniformLocation(self.program, b'uPMatrix') self.mvMatrixUniform = glGetUniformLocation(self.program, b"uMVMatrix") self.bMatrixU = glGetUniformLocation(self.program, b"bMatrix") self.colorU = glGetUniformLocation(self.program, b"uColor") self.samplerU = glGetUniformLocation(self.program, b"uSampler") self.posU = glGetUniformLocation(self.program, b"uPos") # attributes self.vertIndex = glGetAttribLocation(self.program, b"aVert") self.texIndex = glGetAttribLocation(self.program, b"aTexCoord") self.time0Index = glGetAttribLocation(self.program, b"aTime0") self.velIndex = glGetAttribLocation(self.program, b"aVel") # render flags self.enableBillboard = True self.disableDepthMask = True self.enableBlend = True # which texture to use self.useStarTexture = True # restart - first time self.restart(numP) # step def step(self): # increment time self.t += 0.01 # restart particle system def restart(self, numP): # set number of particles self.numP = numP # time variables self.t = 0.0 self.lifeTime = 5.0 # color self.col0 = numpy.array([random.random(), random.random(), random.random(), 1.0]) # create Vertex Arrays Object (VAO) self.vao = glGenVertexArrays(1) # bind VAO glBindVertexArray(self.vao) # create attribute arrays and vertex buffers: # vertices s = 0.2 quadV = [ -s, s, 0.0, -s, -s, 0.0, s, s, 0.0, s, -s, 0.0, s, s, 0.0, -s, -s, 0.0 ] vertexData = numpy.array(numP*quadV, numpy.float32) self.vertexBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer) glBufferData(GL_ARRAY_BUFFER, 4*len(vertexData), vertexData, GL_STATIC_DRAW) # texture coordinates quadT = [ 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0 ] tcData = numpy.array(numP*quadT, numpy.float32) self.tcBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.tcBuffer) glBufferData(GL_ARRAY_BUFFER, 4*len(tcData), tcData, GL_STATIC_DRAW) # time lags timeData = numpy.repeat(0.005*numpy.arange(numP, dtype=numpy.float32), 4) self.timeBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.timeBuffer) glBufferData(GL_ARRAY_BUFFER, 4*len(timeData), timeData, GL_STATIC_DRAW) # velocites velocities = [] # cone angle coneAngle = math.radians(20.0) # set up particle velocities for i in range(numP): # inclination angleRatio = random.random() a = angleRatio*coneAngle # azimuth t = random.random()*(2.0*math.pi) # get veocity on sphere vx = math.sin(a)*math.cos(t) vy = math.sin(a)*math.sin(t) vz = math.cos(a) # speed decreases with angle speed = 15.0*(1.0 - angleRatio*angleRatio) # add a set of calculated velocities velocities += 6*[speed*vx, speed*vy, speed*vz] # set up velocity vertex buffer self.velBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.velBuffer) velData = numpy.array(velocities, numpy.float32) glBufferData(GL_ARRAY_BUFFER, 4*len(velData), velData, GL_STATIC_DRAW) # enable arrays glEnableVertexAttribArray(self.vertIndex) glEnableVertexAttribArray(self.texIndex) glEnableVertexAttribArray(self.time0Index) glEnableVertexAttribArray(self.velIndex) # set buffers glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer) glVertexAttribPointer(self.vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None) glBindBuffer(GL_ARRAY_BUFFER, self.tcBuffer) glVertexAttribPointer(self.texIndex, 2, GL_FLOAT, GL_FALSE, 0, None) glBindBuffer(GL_ARRAY_BUFFER, self.velBuffer) glVertexAttribPointer(self.velIndex, 3, GL_FLOAT, GL_FALSE, 0, None) glBindBuffer(GL_ARRAY_BUFFER, self.timeBuffer) glVertexAttribPointer(self.time0Index, 1, GL_FLOAT, GL_FALSE, 0, None) # unbind VAO glBindVertexArray(0) # render the particle system def render(self, pMatrix, mvMatrix, camera): # use shader glUseProgram(self.program) # set projection matrix glUniformMatrix4fv(self.pMatrixUniform, 1, GL_FALSE, pMatrix) # set modelview matrix glUniformMatrix4fv(self.mvMatrixUniform, 1, GL_FALSE, mvMatrix) # set up a billboard matrix to keep quad aligned to view direction if self.enableBillboard: N = camera.eye - camera.center N /= numpy.linalg.norm(N) U = camera.up U /= numpy.linalg.norm(U) R = numpy.cross(U, N) U2 = numpy.cross(N, R) bMatrix = numpy.array([R[0], U2[0], N[0], 0.0, R[1], U2[1], N[1], 0.0, R[2], U2[2], N[2], 0.0, 0.0, 0.0, 0.0, 1.0], numpy.float32) glUniformMatrix4fv(self.bMatrixU, 1, GL_TRUE, bMatrix) else: # identity matrix bMatrix = numpy.array([1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0], numpy.float32) glUniformMatrix4fv(self.bMatrixU, 1, GL_FALSE, bMatrix) # set start position glUniform3fv(self.posU, 1, self.startPos) # set time glUniform1f(self.timeU, self.t) #set lifetime glUniform1f(self.lifeTimeU, self.lifeTime) # set color glUniform4fv(self.colorU, 1, self.col0) # enable texture glActiveTexture(GL_TEXTURE0) glBindTexture(GL_TEXTURE_2D, self.texid) glUniform1i(self.samplerU, 0) # turn depth mask off if self.disableDepthMask: glDepthMask(GL_FALSE) # enable blending if self.enableBlend: glBlendFunc(GL_SRC_ALPHA, GL_ONE) glEnable(GL_BLEND) # bind VAO glBindVertexArray(self.vao) # draw glDrawArrays(GL_TRIANGLES, 0, 6*self.numP) # unbind VAO glBindVertexArray(0) # disable blend if self.enableBlend: glDisable(GL_BLEND) # turn depth mask on if self.disableDepthMask: glDepthMask(GL_TRUE) # disable texture glBindTexture(GL_TEXTURE_2D, 0)

这是火花喷泉的所有代码，但我们还要画一个红色的盒子代表喷泉粒子系统的来源。

## 10.5 盒子代码要让观众的注意力集中于喷泉，只要画一个没有任何灯光的红色立方体就行了。import sys, random, math import OpenGL from OpenGL.GL import * import numpy import glutils strVS = """ #version 330 core in vec3 aVert; uniform mat4 uMVMatrix; uniform mat4 uPMatrix; out vec4 vCol; void main() { // apply transformations gl_Position = uPMatrix * uMVMatrix * vec4(aVert, 1.0); // set color vCol = vec4(0.8, 0.0, 0.0, 1.0); } """ strFS = """ #version 330 core in vec4 vCol; out vec4 fragColor; void main() { // use vertex color fragColor = vCol; } """ class Box: def __init__(self, side): self.side = side # load shaders self.program = glutils.loadShaders(strVS, strFS) glUseProgram(self.program) s = side/2.0 vertices = [ -s, s, -s, -s, -s, -s, s, s, -s, s, -s, -s, s, s, -s, -s, -s, -s, -s, s, s, -s, -s, s, s, s, s, s, -s, s, s, s, s, -s, -s, s, -s, -s, s, -s, -s, -s, s, -s, s, s, -s, -s, s, -s, s, -s, -s, -s, -s, s, s, -s, s, -s, s, s, s, s, s, -s, s, s, s, -s, s, -s, -s, -s, s, -s, -s, -s, -s, s, s, -s, s, -s, -s, s, s, -s, -s, -s, s, -s, s, s, -s,-s, s, s, s, s, s, -s, s, s, s, s, -s,-s ] # set up vertex array object (VAO) self.vao = glGenVertexArrays(1) glBindVertexArray(self.vao) # set up VBOs vertexData = numpy.array(vertices, numpy.float32) self.vertexBuffer = glGenBuffers(1) glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer) glBufferData(GL_ARRAY_BUFFER, 4*len(vertexData), vertexData, GL_STATIC_DRAW) #enable arrays self.vertIndex = glGetAttribLocation(self.program, "aVert") glEnableVertexAttribArray(self.vertIndex) # set buffers glBindBuffer(GL_ARRAY_BUFFER, self.vertexBuffer) glVertexAttribPointer(self.vertIndex, 3, GL_FLOAT, GL_FALSE, 0, None) # unbind VAO glBindVertexArray(0) def render(self, pMatrix, mvMatrix): # use shader glUseProgram(self.program) # set projection matrix glUniformMatrix4fv(glGetUniformLocation(self.program, 'uPMatrix'), 1, GL_FALSE, pMatrix) # set modelview matrix glUniformMatrix4fv(glGetUniformLocation(self.program, 'uMVMatrix'), 1, GL_FALSE, mvMatrix) # bind VAO glBindVertexArray(self.vao) # draw glDrawArrays(GL_TRIANGLES, 0, 36) # unbind VAO glBindVertexArray(0)

盒子的代码使用简单的顶点和片段着色器来绘制一个立方体。这里使用的概念与本章前面和第9章中讨论的相同。

## 10.6 主程序代码该项目的主程序源文件是psmain.py，它设置了GLFW窗口，处理了键盘事件，并创建粒子系统。如果想看到完整的程序代码，请跳到10.7节。class PSMaker: """GLFW Rendering window class for Particle System""" def __init__(self): 1. self.camera = Camera([15.0, 0.0, 2.5], [0.0, 0.0, 2.5], [0.0, 0.0, 1.0]) self.aspect = 1.0 self.numP = 300 self.t = 0 # flag to rotate camera view self.rotate = True # save current working directory cwd = os.getcwd() # initialize glfw; this changes cwd 2. glfw.glfwInit() # restore cwd os.chdir(cwd) # version hints glfw.glfwWindowHint(glfw.GLFW_CONTEXT_VERSION_MAJOR, 3) glfw.glfwWindowHint(glfw.GLFW_CONTEXT_VERSION_MINOR, 3) glfw.glfwWindowHint(glfw.GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE) glfw.glfwWindowHint(glfw.GLFW_OPENGL_PROFILE, glfw.GLFW_OPENGL_CORE_PROFILE) # make a window self.width, self.height = 640, 480 self.aspect = self.width/float(self.height) self.win = glfw.glfwCreateWindow(self.width, self.height, b"Particle System") # make context current glfw.glfwMakeContextCurrent(self.win) # initialize GL glViewport(0, 0, self.width, self.height) glEnable(GL_DEPTH_TEST) glClearColor(0.2, 0.2, 0.2,1.0) # set window callbacks glfw.glfwSetMouseButtonCallback(self.win, self.onMouseButton) glfw.glfwSetKeyCallback(self.win, self.onKeyboard) glfw.glfwSetWindowSizeCallback(self.win, self.onSize) # create 3D 3. self.psys = ParticleSystem(self.numP) 4. self.box = Box(1.0) # exit flag 5. self.exitNow = False

类PSMaker创建粒子系统，处理GLFW窗口，并负责渲染喷泉和表示其源头的盒子。在1. 行，创建一个Camera对象，它可以用于在OpenGL中设置观看参数。从2. 行开始的代码块设置了GLFW窗口，在3. 行，创建ParticleSystem对象，在4. 行，创建Box对象。在5. 行，是在主GLFW渲染循环中使用的退出标志，接下来你会看到。

### 10.6.1 每步更新这些粒子通过在主程序循环中更新一个时间变量，我们创建了动画。主程序循环进而又更新顶点着色器中的时间变量。用这个新时间值，计算并渲染下一帧，从而更新这些粒子的位置。着色器计算粒子的新朝向，也让它们旋转。此外，着色器计算alpha值，它是时间变量的函数，将用于最后的渲染，实现火花逐渐淡出。

step()方法为每个时间步骤更新粒子系统。 def step(self): # increment time 1. self.t += 10 2. self.psys.step() # rotate eye if self.rotate: 3. self.camera.rotate() # restart every 5 seconds if not int(self.t) % 5000: 4. self.psys.restart(self.numP)

在1. 行，增加时间变量，它以毫秒为单位记录流逝的时间。在2. 行，调用ParticleSystem的step()方法，这样它可以自行更新。如果设置了标志，就在3. 行旋转相机。每5秒钟（5000毫秒），粒子系统在4. 行重新启动.

### 10.6.2 键盘处理程序现在，来看看GLFW窗口的键盘处理程序。1. def onKeyboard(self, win, key, scancode, action, mods): #print 'keyboard: ', win, key, scancode, action, mods if action == glfw.GLFW_PRESS: # ESC to quit if key == glfw.GLFW_KEY_ESCAPE: self.exitNow = True elif key == glfw.GLFW_KEY_R: self.rotate = not self.rotate elif key == glfw.GLFW_KEY_B: # toggle billboarding self.psys.enableBillboard = not self.psys.enableBillboard elif key == glfw.GLFW_KEY_D: # toggle depth mask self.psys.disableDepthMask = not self.psys.disableDepthMask elif key == glfw.GLFW_KEY_T: # toggle transparency self.psys.enableBlend = not self.psys.enableBlend

1. 行的键盘处理程序，主要在关闭用于绘制粒子系统的各种渲染技巧时，让你很容易看到所发生的事情。这段代码让你切换旋转、公告板、深度遮掩和透明度。

### 10.6.3 管理主程序循环使用GLFW时，必须管理自己的主程序循环。下面是这个程序中使用的循环： def run(self): # initializer timer glfw.SetTime(0) t = 0.0 1. while not glfw.glfwWindowShouldClose(self.win) and not self.exitNow: # update every x seconds 2. currT = glfw.glfwGetTime() if currT - t > 0.01: # update time t = currT # clear glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # render pMatrix = glutils.perspective(100.0, self.aspect, 0.1, 100.0) # modelview matrix mvMatrix = glutils.lookAt(self.camera.eye, self.camera.center, self.camera.up) # draw nontransparent object first 3. self.box.render(pMatrix, mvMatrix) # render 4. self.psys.render(pMatrix, mvMatrix, self.camera) # step 5. self.step() glfw.glfwSwapBuffers(self.win) # poll for and process events glfw.glfwPollEvents() # end glfw.glfwTerminate()

这段代码与第9章中使用的循环几乎是相同的。在1. 行，如果exit标志已设置或GLFW窗口关闭，while循环就退出。在2. 行和后面一行，使用GLFW计时器，仅当时间流逝一定量（0.1秒）时才进行渲染，从而控制渲染的帧速率。在3. 行绘制盒子，在4. 行绘制粒子系统（渲染的顺序很重要：透明物体总是最后绘制，这样它们能够与场景中不透明的物体正确地混合和深度缓冲）。在5. 行，针对当前时间步骤更新粒子系统。

## 10.8 运行程序要运行该项目，请输入以下命令：$ python3 psmain.py

本章开始的图10-1展示了输出。

## 10.10 实验下面有一些想法，可以用更多的方式来试验粒子系统动画。

1．如果每个粒子的喷射没有时间延迟，看看情况如何。

2．让喷泉中的粒子在喷射时逐渐变大（提示：缩放顶点着色器的四顶点）。

3．这些代码让每个粒子遵循完美的抛物线，因为它从喷泉喷出。请为粒子的路径增加一些随机性（提示：研究GLSL的noise()方法，你可以在顶点着色器中使用）。

4．在喷泉中的粒子遵循抛物线轨迹，上升，然后由于重力作用下落。你能让它们跌落到地板时反弹吗？可能需要增加粒子的寿命来实现（提示：地板位于z = 0.0处。在顶点着色器中，当粒子接近地面时，反转速度的z分量）。

# 第五部分玩转硬件

"系统中的那些可以用锤子击打（不建议这么做）的部分称为硬件，

那些只能咒骂的程序指令称为软件。"

--佚名

# 第12章 Arduino简介

Arduino是一个简单的微控制器板卡，是基于可编程芯片的开源开发环境。所有版本的Arduino都包含计算机的标准组件，如内存、处理器和输入/输出系统。

在本章中，我们将在Arduino的帮助下开始进入微控制器的世界。我们将学习Arduino平台的基础知识，以及如何用Arduino编程语言（C++的一个版本）构建Arduino程序。我们将学习如何对Arduino进行编程，从一个简单的光传感器电路收集数据，然后通过串行端口将数据发送给计算机。接下来，我们将用pySerial通过串口与Arduino交互，收集数据，并用matplotlib实时绘制图形。新值输入时，图形将向右滚动，就像EKG监视器一样。其电路设置如图12-1所示。

图12-1 简单的光敏电阻（LDR）电路，在面包板上搭建，并连接到Arduino Uno

## 12.1 Arduino

Arduino是围绕一类名为Atmel AVR的微控制器芯片构建的平台。市场上有许多不同尺寸和功能的Arduino板。图12-2突出了Arduino Uno板卡的一些主要组件，这是比较常见的、可以获得的板卡。Arduino板上的接头（如图12-2所示）允许你访问微控制器的模拟和数字引脚，以便通过发送和接收数据，与其他电子设备通信。（我推荐阅读John Boxall的《Arduino Workshop》一书[No Starch Press，2013]，以便更好地理解Arduino的电子和编程知识。）

图12-2 Arduino Uno板卡的组件注意虽然本书的项目中使用Arduino Uno板，但你应该能够使用非官方的板卡。如果打算这样做，请参阅Arduino网站（http://arduino.cc/），了解板卡之间的区别。例如，一些板卡的引脚编号惯例与Uno不同。

Arduino Uno有一个微控制器芯片，一个通用串行总线（USB）连接，一个用于外部电源的插孔，一些数字输入/输出引脚，一些模拟引脚，可供外部电路使用的电源输出，甚至有直接对芯片编程的引脚。

Arduino板卡包括一个"引导加载程序（bootloader）"，它是一个程序，让你上传代码并在微控制器上运行。如果没有引导加载程序，则要用"在线串行编程技术（ICSP）"与微控制器进行交互（通过名为ICSP头的外部编程引脚，Arduino支持了ICSP）。Arduino易于编程，因为可以通过USB端口将它连接到计算机，并用Arduino软件将代码上传到电路板。

Arduino板卡最重要的组件是AVR微控制器，它是一个单片计算机。Arduino Uno上的AVR微控制器是一个ATmega328芯片。它有中央处理单元（CPU）、定时器/计数器、模拟和数字引脚、存储器模块和时钟模块等。芯片的CPU执行上传的程序。定时器/计数器模块可用于在程序内创建周期性事件（例如每秒检查某个数字引脚的值）。模拟引脚使用模数转换器（ADC）模块将输入的模拟信号转换为数字值，数字引脚可以作为输入或输出，具体取决于如何设置。

## 12.2 Arduino生态系统

Arduino处在一个生态系统的中心，这个生态系统将编程语言与集成开发环境（IDE）、支持性和创造性的社区以及大量外设结合起来。

### 12.2.1 语言

Arduino编程语言是C++的简化版本，起源于处理和布线（Processing and Wiring）原型语言。它的设计目的是让不熟悉编程的人容易使用。为Arduino编写的程序称为"草图（sketches）"（有关Arduino编程语言的更多信息，请访问http://arduino.cc/）。

### 12.2.2 IDE

Arduino包括一个简单的IDE，可以在其中创建草图并上传到Arduino（参见图12-3）。IDE还包括一个"串行监视器（serial monitor）"，可以通过让Arduino经串口向计算机发送信息，来调试应用程序。此外，IDE还包括几个示例程序，以及一系列标准库，用于执行常见任务，并与外部的外设板卡接口。

图12-3 Arduino IDE中的示例程序

### 12.2.3 社区

Arduino有一个庞大的用户群，如果对一个项目有疑问，你可以向Arduino社区寻求帮助。Arduino社区已经开发了许多开源库，可以在你的项目中使用，如果用Arduino连接一些传感器模块时遇到困难，很可能有人已经解决了这个问题，并提供了一个库，使你的生活更轻松。

### 12.2.4 外设与所有流行的平台一样，围绕Arduino平台建立了一个产业。大量的功能扩展板（可以方便地安装在Arduino上，以便访问传感器和其他电子元件的板卡）、分线板（可以方便地连接难以焊接的元件/电路）和其他外设，都可用于Arduino，其中许多可以让你的项目更简单。SparkFun Electronics（https://www.sparkfun.com/ ）和Adafruit Industries（http://www.adafruit.com/ ）是两家公司，它们分别提供了许多可与Arduino一起使用的产品。

## 12.4 搭建感光电路首先，我们将搭建感光电路，它由两个常规电阻和两个LDR组成。图12-4展示了感光电路的电路图（附录B包含如何开始搭建电子电路的一些基本信息）。

在图12-4中，VCC表示连接到Arduino的5V输出，它为电路供电。标记为LDR1和LDR2的元件是两个光敏电阻，A0和A1是Arduino的模拟引脚0和1（这些模拟引脚允许微控制器从外部电路读取电压电平）。你还可以看到电阻R1和R2，以及接地（GND）连接，它可以是Arduino上的任何GND引脚。可以在面包板（带弹簧夹的塑料板，用于在不焊接的情况下组装电路）上搭建电路，用少量电线连接，如图12-1所示。

### 12.4.1 电路工作原理在该电路中，每个LDR和它下面的电阻，构成了"电阻分压器"，这是一个简单电路，用两个电阻将输入电压分为两部分。该设置意味着A0处的电压计算如下：

R1 是电阻的阻值，RLDR 是LDR的阻值。V 是电源电压，V0 是R1 两端的电压。随着照在LDR上的光强度改变，它的电阻也改变，因此它两端的电压也相应地改变。电压（0至5伏特之间）在A0处读取，并作为10位值发送给程序，范围为[0,1023]。即电压范围映射为[0,1023]的整数。

在电路中使用的R1 和R2 电阻的值取决于选择的LDR。如果用光照LDR，其电阻会降低，因此RLDR 减小，这意味着V0 增加，Arduino从连接到该LDR的模拟引脚处读入较高的值。要确定R1 和R2 所需的电阻值，请在不同光线条件下用万用表测量LDR的电阻，并将该值代入电压公式。你希望在使用LDR的光照变化场景下，电压有良好的变化（从0V到5V）。

我最后用了4.7k欧姆电阻作为R1 和R2 ，因为我的LDR的电阻从大约10k欧姆（在黑暗中）变化到1k欧姆（在明亮的光线中）。将这些值代入上一个公式中，会看到模拟输入需要1.6V至4V的电压范围。构建电路时，可以从4.7k欧姆电阻开始，并根据需要更改它们。

图12-4 简单感光电路的示意图

### 12.4.2 Arduino程序现在来编写Arduino程序。下面是运行在Arduino上的代码，让它从电路读取信号，并通过串口将它们发送给计算机：

#include "Arduino.h" void setup() { // initialize serial communications 1. Serial.begin(9600); } void loop() { // read A0 2. int val1 = analogRead(0); // read A1 3. int val2 = analogRead(1); // print to serial 4. Serial.print(val1); Serial.print(" "); Serial.print(val2); Serial.print("\n"); // wait 5. delay(50); }

在1. 行，在setup()方法中启用串口通信。因为setup()仅在程序启动时调用，所以这是放置所有初始化代码的好地方。这里将串口通信的波特率（速度，以位/秒为单位）初始化为9600，这是大多数设备的默认值，对你的任务来说也足够快了。

主要代码位于loop()方法中。在2. 行，从模拟引脚0（范围在[0,1023]中的一个10位整数）读取当前信号值，在3. 行，从引脚1读取当前信号值。在4. 行和随后几行，用Serial.print()将值发送给计算机，格式化为两个整数，以空格分隔，后跟换行符。在5. 行，用delay()延缓操作指定的时间，在这里是50毫秒，然后循环重复。这里采用的值决定了AVR微控制器执行loop()方法的速度。

为了将程序上传到Arduino，将Arduino连接到计算机，启动其IDE，并启动一个新项目。然后在程序窗口中输入代码，单击Verify以编译代码。IDE将显示所有和语法相关的错误与警告。如果一切正常，单击Upload将草图发送给Arduino。如果在这个阶段没有看到任何错误，从Arduino软件的工具菜单中调出串口监视器，应该看到类似这样的结果：512 300 513 280 400 200 ...

这些是从模拟引脚0和1读取的模拟值，并通过Arduino的USB口串行发送给计算机。

### 12.4.3 创建实时图表为了在项目中实现滚动的实时图，需要使用一个deque，如第4章所述。deque由N个值的数组构成，在任一端添加和删除值都能很快完成。新值出现时，它们被添加到deque，并且最老的值被弹出。以固定间隔绘制这些值，就会生成实时图，其中最新的数据总是在左侧添加。

## 12.5 Python代码现在来看看从串口读取数据的Python程序（完整的项目代码，请跳到12.6节）。为了更好地组织代码，我们定义一个类AnalogPlot，它保存要绘制的数据。下面是该类的构造函数：class AnalogPlot: # constructor def __init__(self, strPort, maxLen): # open serial port 1. self.ser = serial.Serial(strPort, 9600) 2. self.a0Vals = deque([0.0]*maxLen) 3. self.a1Vals = deque([0.0]*maxLen) 4. self.maxLen = maxLen

在1. 行，AnalogPlot的构造函数利用pySerial库创建一个Serial对象。我们将用该类与Arduino的串口通信。Serial构造函数的第一个参数是端口名称字符串，可以在IDE中通过选择Tools Serial Port找到它（在Windows上，该字符串类似于COM3，在Linux和OS X上，类似于/dev/tty.usbmodem411）。Serial构造函数的第二个参数是波特率，我们设置为9600，以匹配Arduino程序中设置的速率。

在2. 行和3. 行，创建了deque对象来保存模拟值。我们使用大小为maxLen的全零列表初始化deque对象，这是在给定时间绘制的值的最大数量。在4. 行，这个maxLen保存在AnalogPlot对象中。

为了实时绘制模拟值，我们用deque对象缓冲最近的值，如AnalogPlot类中所示。 # add data def add(self, data): assert(len(data) == 2) 1. self.addToDeq(self.a0Vals, data[0]) 2. self.addToDeq(self.a1Vals, data[1]) # add to deque; pop oldest value def addToDeq(self, buf, val): 3. buf.pop() 4. buf.appendleft(val)

正如你前面看到的，Arduino每行仅发送两个模拟整数值。在add()方法中，在1. 行和2. 行，每个模拟引脚的数据值都用addToDeq()方法添加到两个deque对象中。在3. 行和4. 行，这个方法用pop()方法从deque的尾部删除最老的值，然后用appendleft()方法将最新的值添加到deque的头部。在绘制来自该deque的值时，最新的值始终显示在图形的左侧。

我们利用matplotlib的animation类，以设置的间隔更新绘图（你可能还记得，在第5章的Boids项目中看到过）。下面是AnalogPlot中的update()方法，它将在绘制动画的每一步中调用： # update plot def update(self, frameNum, a0, a1): try: 1. line = self.ser.readline() 2. data = [float(val) for val in line.split()] # print data if(len(data) == 2): 3. self.add(data) 4. a0.set_data(range(self.maxLen), self.a0Vals) 5. a1.set_data(range(self.maxLen), self.a1Vals) except: 6. pass return a0, a1

在1. 行，update()方法将一行串口数据读入为一个字符串，在2. 行，利用Python的列表解析，将值转换为浮点数，并保存在列表中。我们用split()方法根据空格来分割字符串，以便将串口读入的字符串512 600\n转换为[512,600]。

检查数据有两个值之后，在3. 行用AnalogPlot的add()方法将值添加到deque。在4. 行和5. 行，利用matplotlib的set_data()方法，用新值更新图形。每次绘图的x值是一系列数字[0，... maxLen]，用range()方法设置。y值用更新的deque对象来填充。

所有这些代码都包含在try语句块中，如果发生异常，代码跳转到6. 行的pass，在这里忽略读入数据（pass不做任何事情）。使用try语句块是因为，串口数据有时可能因电路中接触不良而损坏，而我们不希望仅仅因为串口发送了一些坏的值，程序就崩溃。

准备退出时，关闭串口以释放所有系统资源，如下所示： # clean up def close(self): # close serial self.ser.flush() self.ser.close()

在main()方法中，需要设置matplotlib动画： # set up animation 1. fig = plt.figure() 2. ax = plt.axes(xlim=(0, maxLen), ylim=(0, 1023)) 3. a0, = ax.plot([], []) 4. a1, = ax.plot([], []) 5. anim = animation.FuncAnimation(fig, analogPlot.update, fargs=(a0, a1), interval=20) # show plot 6. plt.show()

在1. 行，取得matplotlib的figure模块，其中包含所有的绘图元素。在2. 行，访问axes模块，设置图形的x和y限制。x限制是样本数，y限制为1023，因为它是模拟值范围的上限。

在3. 行和4. 行，创建两个空白行对象（a0和a1），我们将它们传递给animation类来设置回调，为每一行提供坐标。然后，在5. 行，传入在每个动画步骤中要调用的analogPlot update()方法，来设置动画。我们还指定了调用该方法的参数，以及以毫秒为单位的时间间隔，这里是20。在6. 行，调用plt.show()来启动动画。

程序的main()方法也是用Python模块argparse来支持命令行选项的地方。 # create parser parser = argparse.ArgumentParser(description="LDR serial") # add expected arguments parser.add_argument('--port', dest='port', required=True) parser.add_argument('--N', dest='maxLen', required=False) # parse args args = parser.parse_args() strPort = args.port # plot parameters maxLen = 100 if args.maxLen: maxLen = int(args.maxLen)

--port参数是必需的。它告诉程序接收数据的串口名称（在Arduino IDE中的Tools Serial Port下找到）。maxLen参数是可选的，用于设置一次绘制的点数（默认值为100个样本）。

## 12.7 运行程序要测试该程序，请组装LDR电路，将Arduino连接到计算机，上传程序，然后运行Python代码。$ python3 --port /dev/tty.usbmodem411 ldr.py

图12-5展示了程序的输出示例，具体来说，是LDR暴露在光下然后覆盖时生成的图。从图中可以看出，当LDR的电阻变化时，Arduino读取的模拟电压也发生变化。中心的高峰发生在我迅速将手放在LDR上时，右侧平坦部分发生在我较慢地移过手时。

图12-5 光敏绘图程序的运行示例这两个LDR具有不同的电阻特性，这就是两条线不完全重合的原因，但是你可以看到，它们以相同的方式对光强的变化做出反应。

## 12.9 实验请尝试对Arduino项目进行如下修改。

1．在程序中，图形从左到右滚动，换言之，新值从左边进来时，较老的值向右移动。请反转滚动方向，使图形从右向左移动。

2．Arduino代码定期读取模拟值，并将它们发送到串口。输入数据可能在某些类型的传感器中存在波动，常见的做法是应用某种类型的滤波，从而平滑数据。请实现LDR数据的均值策略（提示：保存每个LDR读取的N个模拟值的移动平均值，平均值应定期发送到串口。减少循环中的delay()，以便更快地读取值。均值图比原始图更平滑吗？尝试不同的N值，看看会发生什么）。

3．传感器电路中有两个LDR。保持这些LDR在良好的光源下，从它们上面用手扫过。你应该看到图形的急剧变化：一个LDR曲线在另一个之前变化，因为它首先被遮挡。可以用这些信息来检测手的运动方向吗？这是一个基本的手势检测项目（提示：LDR中图形的急剧变化发生在不同的时间，说明哪个LDR先被遮蔽，从而给出手的运动方向）。

# 第13章激光音乐秀在第12章中，我们学习了Arduino的基础知识，这很适合与底层电子设备接口。在本项目中，我们将利用Arduino搭建硬件，通过音频信号产生有趣的激光图案。这一次，Python会承担更重的任务。除了处理串口通信之外，它还会基于实时音频数据进行计算，并利用该数据来调整激光显示设备中的电机。

出于这些目的，请将激光当作一束强烈的光束，即使通过很大距离投射，它仍保持聚焦在一个微小的点上。这种聚焦是可能的，因为光束被组织成光波只沿一个方向行进，且彼此同相。这个项目将用一个便宜的、容易获得的激光笔来创建激光图案，与音乐同步（或任何音频输入）。我们用激光笔和两个连接到电机的旋转镜，来构建生成有趣图案的硬件。我们用Arduino设置电机的方向和旋转速度，利用Python通过串口来控制。Python程序将读取音频输入，分析它，并将它转换为电机速度和方向数据来控制电机。我们还将学习如何设置电机的速度和方向，让图案与音乐同步。

本项目将进一步提升你的Arduino和Python知识。以下是将要介绍的一些主题：

- 用激光和两个旋转镜产生有趣的图案；

- 用快速傅立叶变换从信号中获得频率信息；

- 用numpy计算快速傅里叶变换；

- 用pyaudio读取音频数据；

- 在计算机和Arduino之间设置串口通信；

- 用Arduino驱动电机。

## 13.1 用激光产生图案为了在此项目中生成激光图案，我们用激光笔和两个镜子连接到两个小型直流电机的轴上，如图13-1所示。如果你平面镜（反射镜A）的表面照射激光，即使电机正在旋转，投影的反射将保持为一个点。因为激光器的反射平面垂直于电机的旋转轴，所以就像镜子根本不旋转一样。

现在，假设镜子与轴成一定角度连接，如图13-1右侧所示（反射镜B）。当轴旋转时，投影点的轨迹是一个椭圆，而且如果电机旋转足够快，观察者会感觉到移动点是连续的形状。

图13-1 平面镜（镜子A）反射单个点。倾斜的镜子（镜子B）的反射在电动机旋转时产生一个圆如果安排镜子，使从镜子A反射的光投影到镜子B上，会怎么样？现在当电机A和电机B旋转时，由反射点产生的图案将是电机A和电机B的两个旋转运动的组合，产生出有趣的图案，如图13-2所示。

产生的图案将取决于两个电机的旋转速度和旋转方向，但是它们类似于在第2章中探讨的万花尺产生的长短辐圆内旋轮线。

### 13.1.1 电机控制我们用Arduino来控制电机的速度和方向。这种设置要小心，确保它可以接受电机相对较高的电压，因为Arduino只能承担这么大的电流，否则会损坏。可以用图13-3（a）所示的SparkFun TB6612FNG外设"分线（breakout）"板来保护Arduino，简化设计并缩短开发时间。利用分线板从Arduino同时控制两个电机。

图13-2 反射激光离开两面旋转的、倾斜的镜子，产生了有趣的复杂图案图13-3 SparkFun电机驱动器1A双通道TB6612FNG

图13-3（b）展示了分线板的焊接背面。引脚名称中的A和B表示两个电机。IN引脚控制电机的方向，01和02引脚为电机供电，PWM引脚控制电机速度。通过写入这些引脚，你可以控制每个电机的旋转方向和速度，而这正是本项目需要的。

注意可以用任何你熟悉的电机控制电路替换该分线板部分，只要适当地修改Arduino程序即可。

### 13.1.2 快速傅里叶变换因为本项目的最终目标是基于音频输入控制电机速度，所以需要能够分析音频的频率。

回顾一下第4章，来自乐器的音调是多种频率或泛音的混合。事实上，任何声音都可以用傅立叶变换分解为成分频率。将傅里叶变换应用于数字信号时，结果称为离散傅里叶变换（DFT），因为数字信号由许多离散样本组成。在本项目中，我们用Python来实现快速傅立叶变换（FFT）算法，计算DFT（在本章中，我将使用FFT来指代算法和结果）。

下面是一个简单的FFT示例。图13-4展示了一个只包含两个正弦波的信号，下面是对应的FFT。上面的波可以用以下等式表示，是两个波相加：

y(t) = 4sin(2π10t) + 2.5sin(2π30t)

图13-4 从音乐中记录的音频信号（上）及相应的FFT（下）

请注意第一个波的表达式中的4和10：4是波的振幅，10是波的频率（以赫兹为单位）。同时，第二个波的振幅是2.5，频率是30。

FFT揭示了波的分量频率及其相对振幅，显示峰值在10 Hz和30 Hz。第一个峰值的强度约为第二个峰值的强度的两倍。

现在来看一个更复杂的例子。图13-5展示了上面的音频信号，以及下面相应的FFT。

图13-5 FFT算法利用振幅信号（上）计算其分量频率（下）

音频输入（或信号）处在"时域"中，因为振幅数据随时间变化。FFT处在"频域"中。注意图13-5中，FFT显示了一系列峰值，显示了信号中各种频率的强度。

要计算FFT，需要一组样本。样本数的选择是有点随意的，但是小的样本规模不能给出信号频率特征的良好图景，还可能意味着更大的计算量，因为每秒需要计算更多的FFT。另一方面，过大的样本规模让信号的变化平均化，因此不会得到信号的"实时"频率响应。对于本项目采用的44100Hz的采样率，2048的样本大小表示大约0.046秒的数据。

对于本项目，我们需要将音频数据分解成它的组成频率，并用该信息控制电机。首先，将频率范围（以Hz为单位）分成3个频段：[0,100]、[100,1000]和[1000，2500]。我们将计算每个频带的平均振幅，每个值将不同程度地影响电机和产生的激光图案，如下所示：

- 低频平均振幅的变化将影响第一个电机的速度；

- 中频平均振幅的变化将影响第二个电机的速度；

- 高频峰值高于某个阈值时，第一个电机将改变方向。

## 13.2 所需模块以下是构建此项目所需物品的列表：

- 一支小激光笔；

- 两个直流电动机，如用于小玩具（额定为9V）的电机；

- 两个小镜子，直径约2.54厘米或更小；

- SparkFun电机驱动器1A双通道TB6612FNG；

- Arduino Uno或类似板卡；

- 连接的电线（单芯连接线，两侧的公插针工作良好）；

- 四节AA电池组；

- 一些乐高模块，将电机和激光笔从安装板上抬起，使镜子可以自由旋转；

- 一个矩形的纸板或丙烯酸树脂板，约20.3厘米×15.2厘米，以安装硬件；

- 一把热胶枪；

- 烙铁。

### 13.2.1 搭建激光秀第一件事是将镜子连接到电机。反射镜必须与电机轴成一个小角度。要安装镜子，将其面朝下放置在平坦的表面上，并在中心滴一滴热胶。小心地将电机轴浸入胶水中，使其垂直于镜子，直到胶水硬化（如图13-6所示）。要测试它，就用手旋转镜子，同时用激光笔照射它。你应该发现反射的激光点投射在平坦表面上时，移动轨迹是一个椭圆中。对第二面镜子也一样操作。

图13-6 以微小角度将反射镜连接到每个电机轴对准镜子接下来，将激光笔与反射镜对准，使激光从反射镜A反射到B，如图13-7所示。确保在反射镜A的整个旋转范围内，来自反射镜A的反射激光保持在反射镜B的圆周内（这需要一些尝试，可能会犯些错）。要测试，请手动旋转反射镜A。另外，确保在两个反射镜的旋转范围内，反射镜B的位置让它反射的光落在一个平面上（如墙上）。

图13-7 激光笔和反射镜的对准注意调整时，需要保持激光笔打开。如果激光笔有一个开启按钮，请用胶带让它保持打开（或者参见13.8节，了解更优雅的控制激光笔电源的方法）。

对镜子的位置感到满意后，将激光笔和两个带有镜子的电机用热熔胶粘到3个一样的乐高模块上，将它们升起，让它们能够自由旋转。接下来，将模块放在安装板上，当你对它们的摆放感到满意时，通过用铅笔记录它们的边缘，标记每个模块的位置。然后将模块粘在板上。为电机供电如果电机没有附带连接到它们的端子上的电线（大多数没有），就将电线焊接到两个端子，确保留出足够的电线（例如15厘米），以便将电机连接到电机驱动板卡上。电机由电池组中的四节AA电池供电，可以用热熔胶将它粘在安装板的背面，如图13-8所示。

现在用手旋转两个镜子来测试硬件，同时用激光照射它们。如果足够快地旋转它们，应该看到一些有趣的图案，窥见结果的样子！

图13-8 将电池组固定在安装板背面

### 13.2.2 连接电机驱动器本项目用Arduino通过Sparkfun电机驱动器（TB6612FNG）来控制电机。我不会详细介绍这个板卡的工作原理，但如果你好奇，可以从了解"H桥"开始，这是一种常见的电路设计，用"金属氧化物半导体场效应晶体管（MOSFET）"来控制电机。

现在将电机连接到SparkFun电机驱动器和Arduino。有不少电线要连接，如表13-1所示。一个电机标记为A，另一个为B，在接线时遵守这个惯例。

表13-1 SparkFun电机驱动器到Arduino的接线从至

Arduino Digital Pin 12 TB6612FNG

Pin BIN2

Arduino Digital Pin 11 TB6612FNG

Pin BIN1

Arduino Digital Pin 10 TB6612FNG

Pin STBY

Arduino Digital Pin 9 TB6612FNG

Pin AIN1

Arduino Digital Pin 8 TB6612FNG

Pin AIN2

Arduino Digital Pin 5 TB6612FNG

Pin PWMB

Arduino Digital Pin 3 TB6612FNG

Pin PWMA

Arduino 5V Pin TB6612FNG

Pin VCC

Arduino GND TB6612FNG

Pin GND

Arduino GND Battery Pack

GND (-)

Battery Pack VCC (+) TB6612FNG

Pin VM

Motor #1 Connector #1 (polarity doesn't matter) TB6612FNG

Pin A01

Motor #1 Connector #2 (polarity doesn't matter) TB6612FNG

Pin A02

Motor #2 Connector #1 (polarity doesn't matter) TB6612FNG

Pin B01

Motor #2 Connector #2 (polarity doesn't matter) TB6612FNG

Pin B02

Arduino USB connector

计算机的USB口图13-9展示了所有接线。

图13-9 完全连好线的激光秀装置现在来看看Arduino程序。

## 13.3 Arduino程序程序开始时，设置Arduino的数字输出引脚。然后，在主循环中，从串口读入数据，并将数据转换为需要发送到电机驱动器板卡的参数。我们还要了解如何实现电机的速度和方向控制。

### 13.3.1 配置Arduino数字输出引脚首先，根据表13-1将Arduino数字引脚映射到电机驱动器上的引脚，并将引脚设置为输出。 // motor A connected to A01 and A02 // motor B connected to B01 and B02 1. int STBY = 10; //standby // Motor A int PWMA = 3; //speed control int AIN1 = 9; //direction int AIN2 = 8; //direction // Motor B int PWMB = 5; //speed control int BIN1 = 11; //direction 2. int BIN2 = 12; //direction void setup(){ 3. pinMode(STBY, OUTPUT); pinMode(PWMA, OUTPUT); pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMB, OUTPUT); pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT); // initialize serial communication 4. Serial.begin(9600); }

从1. 行到2. 行，将Arduino引脚的名称映射到电机驱动器引脚。例如，PWMA（脉冲调制A）控制电机A的速度，并分配给Arduino引脚3。PWM是为设备供电的一种方式，通过发送快速打开和关闭的数字脉冲，让器件"看到"连续的电压。数字脉冲接通的时间部分称为"占空比"，以百分比表示。通过更改这个百分比，可以为设备提供不同的功率水平。PWM通常用于控制可调光LED和电机速度。

然后，在3. 行调用setup()方法，在后续几行中，将所有7个数字引脚设置为输出。在4. 行，开始串口通信，读取由Arduino上的计算机发送的串行数据。

### 13.3.2 主循环程序中的主循环等待串行数据到达，解析它以提取电机速度和方向，并利用该信息来设置控制电机的驱动板的数字输出。// main loop that reads the motor data sent by laser.py void loop() { // data sent is of the form 'H' (header), speed1, dir1, speed2, dir2 1. if (Serial.available() >= 5) { 2. if(Serial.read() == 'H') { // read the next 4 bytes 3. byte s1 = Serial.read(); byte d1 = Serial.read(); byte s2 = Serial.read(); byte d2 = Serial.read(); // stop the motor if both speeds are 0 4. if(s1 == 0 && s2 == 0) { stop(); } else { // set the motors' speed and direction 5. move(0, s1, d1); move(1, s2, d2); } // slight pause for 20 ms 6. delay(20); } else { // if there is invalid data, stop the motors 7. stop(); } } else { // if there is no data, pause for 250 ms 8. delay(250); } }

电机控制数据以5个字节为一组发送：H后跟4个单字节数字s1、d1、s2和d2，表示电机的速度和方向。由于串行数据连续输入，所以在1. 行，检查并确保已收到至少5个字节。如果没有，就延迟250毫秒8. ，并尝试在下一个周期中再次读取数据。

在2. 行，检查读入的第一个字节是一个H，以确保在一组正确的控制数据的开始处，接下来的4个字节是期望的数据。如果不是，就在7. 行停止电机，因为数据可能因传输或连接错误而被损坏。

从3. 行开始，程序读取两个电机的速度和方向数据。如果两个电机速度都设置为零，就停止电机4. 。如果不是，则在5. 行用move()方法将速度和方向值分配给电机。在6. 行，在数据读取中添加一个小延迟，让电机能跟上，确保没有太快地读入数据。

下面是用于设置电机速度和方向的move()方法：// set motor speed and direction // motor: A -> 1, B -> 0 // direction: 1/0 void move(int motor, int speed, int direction) { // disable standby 1. digitalWrite(STBY, HIGH); 2. boolean inPin1 = LOW; boolean inPin2 = HIGH; 3. if(direction == 1){ inPin1 = HIGH; inPin2 = LOW; } if(motor == 1){ 4. digitalWrite(AIN1, inPin1); digitalWrite(AIN2, inPin2); analogWrite(PWMA, speed); } else{ 5. digitalWrite(BIN1, inPin1); digitalWrite(BIN2, inPin2); analogWrite(PWMB, speed); } }

电机驱动器具有待机模式，以便在电机关闭时节省电力。在1. 行，通过写入HIGH到待机引脚，退出待机。在2. 行，定义两个布尔变量，它们确定电机的旋转方向。在3. 行，如果direction参数设置为1，则翻转这些变量的值，这让你在下面的代码中切换电机的方向。

在4. 行，为电机A设置引脚AIN1、AIN2和PWMA。引脚AIN1和AIN2控制电机的方向，根据需要，我们用Arduino的digitalWrite()方法将一个引脚设置为HIGH（1），一个设置为LOW（0）。对于引脚PWMA，我们发送PWM信号，如前所述，这可以控制电机的速度。要控制PWM的值，可以用analogWrite()方法将范围[0,255]内的值写入Arduino输出引脚（不同的是，digitalWrite()方法只允许将1或0写入输出引脚）。

在5. 行，设置电机B的引脚。

### 13.3.3 停止电机要停止电机，将LOW写入电机驱动器的待机引脚。void stop(){ //enable standby digitalWrite(STBY, LOW); }

## 13.4 Python代码现在来看看在计算机上运行的Python代码。这段代码完成了繁重的工作：它读入音频，计算FFT，并发送串行数据到Arduino。可以在13.5节中找到完整的项目代码。

### 13.4.1 选择音频设备首先，需要利用pyaudio模块读入音频数据。初始化pyaudio模块如下：p = pyaudio.PyAudio()

接下来，可以用pyaudio中的辅助函数访问计算机的音频输入设备。getInputDevice()方法的代码如下所示：

# get pyaudio input device def getInputDevice(p): 1. index = None 2. nDevices = p.get_device_count() print('Found %d devices. Select input device:' % nDevices) # print all devices found for i in range(nDevices): 3. deviceInfo = p.get_device_info_by_index(i) 4. devName = deviceInfo['name'] 5. print("%d: %s" % (i, devName)) # get user selection try: # convert to integer 6. index = int(input()) except: pass # print the name of the chosen device if index is not None: devName = p.get_device_info_by_index(index)["name"] print("Input device chosen: %s" % devName) 7. return index

在1. 行，将index变量设置为None（该index是7. 行的函数返回值，如果返回为None，则表明找不到合适的输入设备）。在2. 行，用get_device_count()方法获取计算机上音频设备的数量，包括所有音频硬件，如麦克风、线路输入或线路输出。然后遍历所有找到的设备，获取每个设备的信息。

3. 行的get_device_info_by_index()函数返回一个字典，其中包含每个音频设备的各种特征信息，但我们只想查看设备的名称，因为我们正在查找输入设备。在4. 行，保存设备名称，在5. 行，打印出设备的索引和名称。在6. 行，利用input()方法读入用户的选择，将读入的字符串转换为整数索引。在7. 行，这个选定的索引从函数返回。

### 13.4.2 从输入设备读取数据选择输入设备后，需要从中读取数据。为此，我们先打开音频流，如下所示（注意，所有的代码在while循环中连续执行）。 # set FFT sample length 1. fftLen = 2**11 # set sample rate 2. sampleRate = 44100 print('opening stream...') 3. stream = p.open(format = pyaudio.paInt16, channels = 1, rate = sampleRate, input = True, frames_per_buffer = fftLen, input_device_index = inputIndex)

在1. 行，将FFT缓冲区的长度（用于计算FFT的音频采样数）设置为2048（是211，FFT算法针对2的幂进行了优化）。然后，将pyaudio的采样率设置为44100，即44.1 kHz 2. ，这是CD质量录音的标准。

接下来，打开pyaudio流3. ，并指定几个选项：

- pyaudio.paInt16表示读取的数据作为16位整数；

- channels设置为1，因为我们将音频作为单个频道读取；

- rate设置为选定的采样速率44100 Hz；

- input设置为True；

- frames_per_buffer设置为FFT缓冲区长度；

- input_device_index设置为我们在getInputDevice()方法中选择的设备。

### 13.4.3 计算数据流的FFT

以下是从流中读取数据的代码： # read a chunk of data 1. data = stream.read(fftLen) # convert the data to a numpy array 2. dataArray = numpy.frombuffer(data, dtype=numpy.int16)

在1. 行，从音频输入流读取最近的fftLen样本。然后在2. 行，将该数据转换为16位整数numpy数组。

现在计算这个数据的FFT。 # get FFT of data 1. fftVals = numpy.fft.rfft(dataArray)*2.0/fftLen # get absolute values of complex numbers 2. fftVals = numpy.abs(fftVals)

在1. 行，用numpy fft模块中的rfft()方法，计算numpy数组中的值的FFT。该方法接受由"实数"（如音频数据）组成的信号并计算FFT，通常结果是一组"复数"。2.0/fftLen是归一化因子，用来将FFT值映射到希望的范围。然后，因为rfft()方法返回复数，所以使用numpy的abs()方法2. 来获取这些复数的大小，它是实数。

### 13.4.4 从FFT值提取频率信息接下来，从FFT值中提取相关的频率信息。 # average 3 frequency bands: 0-100 Hz, 100-1000 Hz, and 1000-2500 Hz levels = [numpy.sum(fftVals[0:100])/100, numpy.sum(fftVals[100:1000])/900, numpy.sum(fftVals[1000:2500])/1500]

为了分析音频信号，我们将频率范围分为3个频段：0至100 Hz、100至1000 Hz和1000至2500 Hz。我们最感兴趣的是较低的低音频段（0-100 Hz）和中音（100-1000 Hz）频段，分别大致对应于一首歌曲中的节拍和人声。对于每个范围，我们在代码中用numpy.sum()方法计算平均FFT值。

### 13.4.5 将频率转换为电机速度和方向现在将该频率信息转换为电机速度和方向。 # 'H' (header), speed1, dir1, speed2, dir2 1. vals = [ord('H'), 100, 1, 100, 1] # speed1 2. vals[1] = int(5*levels[0]) % 255 # speed2 3. vals[3] = int(100 + levels[1]) % 255 # dir d1 = 0 4. if levels[2] > 0.1: d1 = 1 vals[2] = d1 5. vals[4] = 0

在1. 行，初始化要发送到Arduino的电机速度和方向值的列表（5个字节，从H开始，前面讨论过）。用内置ord()函数将字符串转换为整数，然后将3个频带的平均值转换为电机速度和方向，填充该列表。

注意这部分确实是自由发挥：没有特别优雅的规则来管理这些转换。这些值随着音频信号而不断变化，你提出的任何方法都可以改变电机速度，并随音乐一起影响激光模式。只需确保转换将电机速度设置在[0,255]范围内，并且方向总是设置为1或0。我选择的方法只是基于试验和错误，我在播放各种类型的音乐时观察FFT值。

在2. 行，从最低频率范围获取值，放大5倍，转换为整数，并用取模运算符（%）确保该值位于[0,255]范围内。该值控制第一电机的速度。在3. 行，将中间频率值加上100，并放在[0,255]范围内。该值控制第二电机的速度。

然后，在4. 行，只要最高频率范围的值超过阈值0.1，就切换电机A方向。电机B的方向保持为05. （通过尝试和错误，我发现，这些方法产生很好的图案变化，但我建议你改变这些值，并创建自己的转换。这里没有错误的答案）。

### 13.4.6 测试电机设置在用实时音频流测试硬件之前，先检查电机设置。这里展示的autoTest()函数就是做这件事的：

# automatic test for sending motor speeds def autoTest(ser): print('starting automatic test...') try: while True: # for each direction combination 1. for dr in [(0, 0), (1, 0), (0, 1), (1, 1)]: # for a range of speeds 2. for j in range(25, 180, 10): 3. for i in range(25, 180, 10): 4. vals = [ord('H'), i, dr[0], j, dr[1]] 5. print(vals[1:]) 6. data = struct.pack('BBBBB', *vals) 7. ser.write(data) sleep(0.1) except KeyboardInterrupt: print('exiting...') # shut off motors 8. vals = [ord('H'), 0, 1, 0, 1] data = struct.pack('BBBBB', *vals) ser.write(data) ser.close()

该方法通过改变每个电机的速度和方向，让两个电机在一定范围内运动。因为每个电动机的方向可以是顺时针或逆时针，所以在1. 行的外层循环中表示4个这样的组合。对于每种组合，2. 行和3. 行的循环以不同的速度运转电机。

注意我使用范围（25，180，10），这意味着速度从25变到180，步长为10。我没有用电机的完整运动范围[0，255]，因为电机很少转速低于25，而200以上的转速真的很快。

在4. 行，生成5字节的电机数据值，在5. 行，打印它们的方向和速度值（使用Python字符串切割vals [1：]将获得除列表中的第一个元素之外的所有内容）。

在6. 行，将电机数据打包到字节数组中，并在7. 行将其写入串口。按Ctrl-C键中断这个测试，在8. 行通过清理来处理这个异常，停止电机并关闭串口，像你这样负责的程序员都会这么做。

### 13.4.7 命令行选项与以前的项目一样，可以用argparse模块来解析程序的命令行参数。

# main method def main(): # parse arguments parser = argparse.ArgumentParser(description='Analyzes audio input and sends motor control information via serial port') # add arguments parser.add_argument('--port', dest='serial_port_name', required=True) parser.add_argument('--mtest', action='store_true', default=False) parser.add_argument('--atest', action='store_true', default=False) args = parser.parse_args()

在这段代码中，串口是必需的命令行选项。还有两个可选的命令行选项：一个用于自动测试（前面介绍过），另一个用于手动测试（稍后将讨论）。

下面是main()方法中解析命令行选项后发生的情况： # open serial port strPort = args.serial_port_name print('opening ', strPort) 1. ser = serial.Serial(strPort, 9600) if args.mtest: manualTest(ser) elif args.atest: autoTest(ser) else: 2. fftLive(ser)

在1. 行，利用pySerial用传入程序的字符串打开一个串口。串行通信的速度或波特率设置为每秒9600位。如果没有使用其他命令参数（--atest或--mtest），则在2. 行继续音频处理和FFT计算，这封装在fftLive()方法中。

### 13.4.8 手动测试这个手动测试允许你输入特定的电机方向和速度，以便看到它们对激光图案的影响。

# manual test of motor direction and speeds def manualTest(ser): print('starting manual test...') try: while True: print('enter motor control info such as < 100 1 120 0 >') 1. strIn = raw_input() 2. vals = [int(val) for val in strIn.split()[:4]] 3. vals.insert(0, ord('H')) 4. data = struct.pack('BBBBB', *vals) 5. ser.write(data) except: print('exiting...') # shut off the motors 6. vals = [ord('H'), 0, 1, 0, 1] data = struct.pack('BBBBB', *vals) ser.write(data) ser.close()

在1. 行，用raw_input()方法等待，直到用户在命令提示符下输入值。预期输入的形式为100 1 120 0，表示电机A的速度和方向，然后是电机B的速度和方向。在2. 行，将字符串解析为整数列表。在3. 行，插入一个"H"构成完整的电机数据，在4. 行和5. 行，打包此数据并通过串口以预期的格式发送。如果用户用Ctrl-C中断测试（或者发生任何异常），就在6. 行完成清理工作，正常关闭电机和串口。

## 13.6 运行程序为了测试本项目，请组装硬件，将Arduino连接到计算机，并将电机驱动程序代码上传到Arduino。确保电池组已连接，激光笔已打开并投射在墙壁这样的平坦表面上。我建议首先通过运行以下程序来测试激光显示部分（不要忘记更改串口字符串以符合你的计算机）！$ python3 laser.py --port /dev/tty.usbmodem411 --atest ('opening ', '/dev/tty.usbmodem1411') staring automatic test... [25, 0, 25, 0] [35, 0, 25, 0] [45, 0, 25, 0] ...

该测试通过速度和方向的各种组合来运转两个电机。你应该看到投射到墙上的不同激光图案。要停止程序和电机，请按Ctrl-C。

如果测试成功，就可以开始真正的激光秀了。在计算机上开始播放你喜欢的音乐，然后运行程序如下。（同样，注意串口字符串！）$ python3 laser.py --port /dev/tty.usbmodem411 ('opening ', '/dev/tty.usbmodem1411') Found 4 devices. Select input device: 0: Built-in Microph 1: Built-in Output 2: BoomDevice 3: AirParrot 0 Input device chosen: Built-in Microph opening stream...

你应该看到激光秀产生了许多有趣的图案，随着音乐和时间变化，如图13-10所示。

图13-10 激光秀的完整布线和投影在墙上的图案

## 13.8 实验下面是修改此项目的一些方法。

1．该程序采用一种自由发挥的方案将FFT值转换为电机速度和方向数据。请尝试修改此方案。例如，尝试使用不同的频带和标准来改变电机的方向。

2．在本项目中，从音频信号收集的频率信息被转换为电机速度和方向。请尝试根据音乐的整体"节奏"或音量来让电机运动。为此，你可以计算信号幅度的"均方根（RMS）"值。该计算类似于FFT计算。读入一组音频数据并放入numpy数组x后，可以按如下方式计算RMS值：rms = numpy.sqrt(numpy.mean(x**2))

此外，回忆一下，项目中振幅表示为16位有符号整数，其最大值为32768（一个要记住的有用数字，用于标准化）。用这个RMS振幅与FFT结合，让激光图案产生更大的变化。

在项目中，我们比较朴素地用了一些胶带来保持激光笔的打开状态，测试并进行硬件设置。能找到更好的方法来控制激光吗？请阅读光隔离器和继电器的相关材料[1] ，这是可以打开和关闭外部电路的设备。要使用这些设备，首先需要改造激光笔，让它可以通过外部开关切换。一种方法是永久地将激光笔的按钮粘接到ON位置，取出电池，并将两个引线焊接到电池触点上。现在就可以用这些电线和激光笔的电池手动打开和关闭激光笔。接下来，通过继电器或光隔离器连接激光笔，并使用Arduino上的数字引脚将其打开，用数字开关替换此方案。如果使用光隔离器，可以直接用Arduino切换激光开关。如果使用继电器，还需要一个驱动器，通常是一个简单的晶体管电路。

有这样的设置后，请添加一些代码，让Python程序运行时，发送一个串行命令到Arduino，在开始之前打开激光笔。

[1] "Relays and Optoisolators," What-When-How, http://what-when-how.com/8051-microcontroller/relays-and-optoisolators/。

# 附录B 基础实用电子学本附录简要介绍了搭建电子电路相关的一些基本术语、组件和工具。电子学是工程学分支，涉及利用有源和无源电子元件，设计和构造电路。

这个主题很大，所以我仅仅论及皮毛[1] 。但从爱好者或DIY（自己动手）的角度来看，你不需要知道一大堆知识，就能开始玩电子电路。你可以在搭建中学习，根据我自己的经验，这是一个有趣的、令人上瘾的爱好。我希望通过快速介绍以下主题，激励你开始阅读这方面的内容，并让你开始设计和搭建自己的电路。

## B.1 常用组件大多数电子部件使用半导体类的材料。半导体具有特殊的电气特性，使其成为电子器件构造的理想选择。

在本节中，我们将介绍电路中使用的一些最常见的组件。图B-1展示了这些组件，以及在电路图中表示它们的符号。

图B-1 常用电子组件及其相应的符号

### B.1.1 面包板面包板是用于原型电子电路的多孔模块。面包板的孔中有带弹簧的夹子，并且以简单的方式互连，容易进行实验。不必焊接每个连接，只要将组件插入面包板，并用电线连接它们。

### B.1.2 光敏电阻（LDR）

LDR是一种电阻器，其电阻随着照在其上的光的强度而减小。它用作电子电路中的光传感器。

### B.1.3 集成电路（IC）

IC是包含完整电子电路的器件。IC非常小，每平方厘米可以包含数十亿晶体管。每个IC通常都有一种特定的应用，制造商的数据表提供了必要的原理图、电气和物理特性，以及示例应用程序，以帮助用户。你可能会遇到的常见IC是555，它的主要用作定时器。

### B.1.4 印刷电路板（PCB）

要制作电子电路，需要一个地方来组装组件。通常在PCB上完成此操作，该PCB由绝缘体组成，绝缘体上有一层或多层导电材料（通常为铜）。导电层成形的方式让它形成电路的布线。

元件作为"通孔"元件或"表面安装"元件安装到PCB上，通过焊接与导电层实现导电连接。

### B.1.5 电线搭电路不能没有电线。我们将使用塑料绝缘的铜线。

### B.1.6 电阻电阻是电路中最常见的元件之一。电阻用于减小电路中的电流或电压，并且根据其阻值（以欧姆为单位）来指定。例如，2.7k欧姆电阻具有2.7千欧姆或2700欧姆的阻值。电阻具有指示其阻值的彩色编码带，以及两个可互换的引线，因为它没有极性。

### B.1.7 发光二极管（LED）

LED是在许多电路中看到的小闪烁的灯。然而，LED是特殊类型的二极管，因此它也具有极性，并需要根据极性连接。它通常与电阻器结合使用，限制流过它的电流，因此不会损坏。不同颜色的LED具有不同的最小"导通"电压。

### B.1.8 电容器电容是有两个引线的器件，用于存储电荷。它是根据电容量来测量的，其单位为法拉。典型电容的电容量以微法（μF）为单位。电容有极化和非极化两种。

### B.1.9 二极管二极管是允许电流仅在一个方向上通过的电子器件。二极管通常用作整流器（将AC电流转换为DC的器件）。二极管有两根引线：阳极和阴极。这意味着它有极性，所以两根引线需要与电路的其余部分正确连接。

### B.1.10 晶体管晶体管可以看成是电子开关。晶体管还可以用作电流或电压的放大器。作为集成电路的基本构件，它是最重要的电子部件之一。晶体管有几种类型，但最常见的是双极型晶体管（BJT）和金属氧化物半导体场效应晶体管（MOSFET）。晶体管通常有三根引线。对于BJT，它们被命名为基极、集电极和发射极，而对于MOSFET，它们被命名为栅极、源极和漏极。当晶体管用作开关时，BJT的基极电流（或MOSFET的栅极电压），是让电流能够流过集电极和发射极的原因，因此它作为开关，控制外部负载，如LED或继电器。

### B.1.11 电池/电源大多数电子设备在3到9伏的小电压下工作，这种电压可以由电池提供，或利用插入墙上交流电源插座的电源适配器提供。

## B.2 基本工具除了刚才描述的组件，你还需要一些基本工具，才能开始搭建电子电路。图B-2展示了业余爱好者的工作台上通常会看到的工具。接下来介绍其中一些基本工具。

图B-2 典型的电子工作台，有万用表、工作灯、夹具、剥线钳、螺丝刀、尖嘴钳、放大镜、焊锡、焊剂、示波器和焊接台

### B.2.1 万用表万用表是用于测量电路的电气特性（例如电压、电流、电容和电阻）的仪器。它还经常用于测量电路中的连续性，这表示电流的连续流动。当你试图调试电路时，万用表是非常有用的。

### B.2.2 烙铁及配件对电路在面包板上工作感到满意后，下一步就是将它转移到PCB上，这需要焊接。焊接是使用加热的填充金属来接合两种金属的过程。填料或焊料，过去含铅，但现在常用无铅焊料合金，这更环保。要焊接元件时，将元件放在PCB上，加上助焊剂（使焊接过程更容易的化学品），然后将热的焊料与烙铁一起使用。焊料冷却时，它在部件和铜箔层之间形成物理结合和电连接。

### B.2.3 示波器示波器是用于测量和显示来自电子电路的电压的仪器。它是分析电压波形的有用工具。例如，可以用它来调试从传感器输出的数字数据，或测量从音频放大器输出的模拟电压。它还有其他专门的测量功能，如快速傅里叶变换（FFT）和均方根（RMS）。

图B-2还展示了搭建电路的一些其他有用的工具：多头螺丝刀、尖嘴钳、剥线钳、用于在焊接时固定PCB的夹具、让工作区域照明良好的台灯、帮助你查看小元件和焊接点的放大镜，以及用于烙铁头的清洁器。

## B.3 搭建电路在搭建电路时，从电路图或原理图开始，它将告诉你组件如何相互连接。通常，你会在面包板上搭建该电路，插入元件并用导线连接它们。测试电路并满意后，你可能会考虑把它移到PCB上。虽然面包板很方便，但它看起来有点乱糟糟，这些松散的电线在部署时会不可靠。

你可以使用通用PCB，它的底部有固定的铜图案，也可以设计自己的PCB。前者很适合小电路。通常，你会焊接元件，利用已经存在的铜箔连接，然后根据需要通过焊接额外的电线来搞定其余部分。图B-3展示了一个简单电路的原理图、面包板原型和PCB结构。

如果你想要非常漂亮的PCB，可以自己设计一个并制造出来，也花费不多。有几个软件包可用于设计PCB，但最常用的（免费）有EAGLE[2] 和KiCad[3] 。EAGLE软件有一个简版是免费的，条件是只用于非营利应用。它有一定的限制（例如，只有两个铜层，最大PCB尺寸为10厘米×8厘米，每个项目一张原理图），但这些对于爱好者来说应该不会有太大的问题。但是，EAGLE的学习曲线有些陡峭，而且我觉得界面有点令人困惑。在开始之前，我建议你先看一些视频教程[4] 。

图B-3 从原理图到面包板原型，再到PCB电路

EAGLE中的典型工作流程如下：首先，在原理图编辑器中创建电路图。为此，需要添加电路中使用的元件，然后连线。EAGLE有大量的元件库，很可能你的组件已经在那些库中列出（EAGLE还允许你创建自己定义的组件）。完成原理图后，EAGLE就可以从中生成一个PCB，从而生成这些元件的物理表示。然后，需要放置元件并完成电路布线，设计PCB上铜箔层的连接路径。典型的EAGLE设计如图B-4所示。左边是原理图，右边是相应的电路板。使用EAGLE需要一些练习，但YouTube教程将帮助你起步。

图B-4 使用EAGLE创建的电路原理图和相应的PCB设计设计了PCB后，你需要制造它。一些制造PCB的技术可以在家里完成[5] ，这可以很有趣，但更专业的技术是将你的设计发送给PCB制造商。这些公司通常接受Gerber设计格式，你可以直接从EAGLE生成这些文件，只需一点设置[6] 。许多公司制造PCB。我接触过一个很好的公司是OSH Park[7] 。

完成了PCB和元件焊接后，要考虑你的项目的外壳。当前的制造技术允许你用激光打印和3D打印等技术，设计并构建专业外观封装。你可以使用2D[8] 和3D[9] 软件的组合来设计你的作品。Rich Decibels的一个项目很好地说明了这里讨论的整个构建过程[10] 。

## B.4 下一步你可以从两个角度来探索实用电子学。第一个是从头开始，学习将简单的电路放在一起，了解模拟和数字电路，最后继续了解微控制器和与计算机的接口电路。另一种方法是从编程的角度开始，即从Arduino和树莓派等硬件友好的板卡开始，然后通过为这些板卡搭建传感器和致动器来了解电路。两种方法都很好，大多数时候你可能会发现自己处于两者之间。

预祝你在电子工程方面取得巨大成功。一旦你创建了某个作品，我希望你花时间记录下来，并与世界分享。在Instructables（http://www.instructables.com/ ）这样的网站上，可以分享你的项目，或从全球其他人的DIY项目中寻找灵感。

[1] 关于电子学的全面参考，我推荐Paul Scherz和Simon Monk的《Practical Electronics for Inventors》第3版（McGraw-Hill，2013）。

[2] CadSoft EAGLE PCB设计软件，http://www.cadsoftusa.com/eagle-pcb-design-software/ 。

[3] KiCad EDA软件套件，http://www.kicad-pcb.org/display/KICAD/KiCad+EDA+Software+Suite/ 。

[4] Jeremy Blum，"Tutorial 1 for Eagle：Schematic Design"，YouTube（2012年6月14日），https：// www.youtube.com/watch?v=1AXwjZoyNno。

[5] 在家里制作PCB的一些技术可以在https://embeddedinn.wordpress.com/tutorials/home-made-sigle-sided-pcbs/找到。

[6] Akash Patel，"Generating Gerber files from EAGLE"，YouTube（2010年4月7日），https://www.youtube.com/watch?v=B_SbQeF83XU。

[7] https://oshpark.com/。

[8] 对于2D软件，请参阅Inkscape，http://www.inkscape.org/en/ 。

[9] 对于3D软件，请参阅SketchUp，http://www.sketchup.com/ 。

[10] Rich Decibels，"Laser-Cut Project Box Tutorial，"Ponoko（2011年8月9日），http://support.ponoko.com/entries/20344437-Laser- cut-project-box-tutorial/。

# 欢迎来到异步社区！

## 异步社区的来历异步社区(www.epubit.com.cn)是人民邮电出版社旗下IT专业图书旗舰社区，于2015年8月上线运营。

异步社区依托于人民邮电出版社20余年的IT专业优质出版资源和编辑策划团队，打造传统出版与电子出版和自出版结合、纸质书与电子书结合、传统印刷与POD按需印刷结合的出版平台，提供最新技术资讯，为作者和读者打造交流互动的平台。

## 社区里都有什么？

### 购买图书我们出版的图书涵盖主流IT技术，在编程语言、Web技术、数据科学等领域有众多经典畅销图书。社区现已上线图书1000余种，电子书400多种，部分新书实现纸书、电子书同步出版。我们还会定期发布新书书讯。

### 下载资源社区内提供随书附赠的资源，如书中的案例或程序源代码。

另外，社区还提供了大量的免费电子书，只要注册成为社区用户就可以免费下载。

### 与作译者互动很多图书的作译者已经入驻社区，您可以关注他们，咨询技术问题；可以阅读不断更新的技术文章，听作译者和编辑畅聊好书背后有趣的故事；还可以参与社区的作者访谈栏目，向您关注的作者提出采访题目。

## 灵活优惠的购书您可以方便地下单购买纸质图书或电子图书，纸质图书直接从人民邮电出版社书库发货，电子书提供多种阅读格式。

对于重磅新书，社区提供预售和新书首发服务，用户可以第一时间买到心仪的新书。

用户帐户中的积分可以用于购书优惠。100积分=1元，购买图书时，在里填入可使用的积分数值，即可扣减相应金额。

特别优惠购买本电子书的读者专享异步社区优惠券 。 使用方法：注册成为社区用户，在下单购书时输入"57AWG "，然后点击"使用优惠码"，即可享受电子书8折优惠（本优惠券只可使用一次）。

### 纸电图书组合购买社区独家提供纸质图书和电子书组合购买方式，价格优惠，一次购买，多种阅读选择。

## 社区里还可以做什么？

### 提交勘误您可以在图书页面下方提交勘误，每条勘误被确认后可以获得100积分。热心勘误的读者还有机会参与书稿的审校和翻译工作。

### 写作社区提供基于Markdown的写作环境，喜欢写作的您可以在此一试身手，在社区里分享您的技术心得和读书体会，更可以体验自出版的乐趣，轻松实现出版的梦想。

如果成为社区认证作译者，还可以享受异步社区提供的作者专享特色服务。

### 会议活动早知道您可以掌握IT圈的技术会议资讯，更有机会免费获赠大会门票。

## 加入异步扫描任意二维码都能找到我们：

异步社区微信订阅号微信服务号官方微博

QQ群：436746675

社区网址： www.epubit.com.cn>

官方微信： 异步社区官方微博： @人邮异步社区，@人民邮电出版社-信息技术分社投稿&咨询： contact@epubit.com.cn
