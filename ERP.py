import math
import pymysql
import datetime
import tkinter

# ------------------------连接MySQL数据库------------------------
connect = pymysql.connect(host='localhost',
                          user='root',
                          password='111111',
                          db='mrp_db',
                          )
# 生成游标对象
cur = connect.cursor()

# ------------------------一些全局变量的定义---------------------------------
# 建立dic字典，记录每个物料对应的库存数
dic = {}
sql = "SELECT  `物料名称`,`工序库存`+`资材库存` a FROM `db_库存表` "
cur.execute(sql)
name = cur.fetchall()
for i in name:
    dic[i[0]] = i[1]
# piece表示所输入要生产商品的批次
piece = 0
# mid用于记录每个结点的编号
mid = -1
# 记录父结点的孩子结点(如果没有则其对应列表为空)
child = list()
# List用于存放商品的信息
List = list()


# ---------------------接收用户输入的初始商品信息-----------------------------
def add():
    global piece
    piece += 1
    # 得到输入商品的名称
    pname = product.get()
    # 得到输入商品的数量
    number = int(quantity.get())
    # 得到输入商品的截止日期,并显示在界面上
    deadl = deadline.get()
    aListbox.insert(piece, f"product：{pname}        quantity:  {number}        deadline:{deadl}", )

    sql1 = "SELECT 作业提前期+配料提前期+供应商提前期 AS pre_time FROM db_库存表 a,db_物料表 b,db_调配构成表 c WHERE a.`物料号`=b.`物料号` AND " \
           "a.`物料号`=c.`子物料号` AND `子物料名称`=%s "
    cur.execute(sql1, pname)
    time = cur.fetchall()[0][0]
    y, m, d = deadl.split('-')
    # 得到父物料的日程下达日期
    fDate = datetime.date(int(y), int(m), int(d)) - datetime.timedelta(time)
    # 公式一：父物料的下达日期=子物料的完成日期，本函数相当于得到表格中第一行信息
    # 深度遍历，得到所有物料的下达日期和完成日期，同时计算权重
    DFS(pname, fDate, -1)
    # 眼镜 2020-5-29 -1


# ------------深度遍历，得到所有商品的开始时间和结束时间和权重------------
def DFS(mName, mDate, no):
    # mDate是该物料开始作业的时间, 也就是他的子物料们结束的时间
    # mid表示当前节点编号
    global mid
    mid += 1
    # 当前节点id
    nId = mid
    # 当前节点的子节点集合, 初始为空
    child.append([])
    # 节点权重，如果有一个子节点，那么权重加1
    weight = 1
    need = int(quantity.get())
    # 判断当前节点是否是根节点
    if no != -1:
        # 如果不是根节点就把当前节点添加到父节点的子节点集合中去,并且把需求量设置为0，后续再确定
        # no是父节点的编号
        child[no].append(nId)
        need = 0

    # 眼镜，100，2020-5-29，0，1
    # 商品名，需求量（除了根节点都初始化为0），该物料的下达日期（子物料的完成日期），当前节点的编号，批次
    List.append([mName, need, mDate, nId, piece])

    # 找到这个结点的子物料
    sql2 = "SELECT `子物料名称`FROM `db_调配构成表`WHERE `父物料名称`=%s"
    cur.execute(sql2, mName)
    cNodes = cur.fetchall()
    for cNode in cNodes:
        # fId表示父亲结点编号
        fId = nId
        sql3 = "SELECT 作业提前期+配料提前期+供应商提前期 AS pre_time FROM db_库存表 a,db_物料表 b,db_调配构成表 c WHERE a.`物料号`=b.`物料号` AND a.`物料号`=c.`子物料号` AND `父物料名称`=%s AND `子物料名称`= %s"
        cur.execute(sql3, (mName, (cNode[0])))
        time = cur.fetchall()[0][0]
        # 公式二：子物料的下达日期=子物料的日程完成期-子物料的作业提前期-子物料配料提前期
        # 得到子物料的下达日期
        cDate = mDate - datetime.timedelta(time)
        # 遍历
        weight += DFS(cNode[0], cDate, fId)
    List[nId].append(weight)
    print(child)
    print(List)
    return weight


# ------------rQuantity函数表示每种商品的真正所需数量------------
def rQuantity(no):
    # 公式三：子物料的需求数量=（父物料的需求数量*子物料的构成数）/(1-损耗率)-工序库存量-资材库存量
    name = List[no][0]  # 眼镜
    # 在字典中查找对应的库存
    mi = min(dic[name], List[no][1])
    dic[name] = dic[name] - mi  # 更新库存
    # !!!!如果是生产型的物料有库存的话，则减去库存!!!!
    # 如果是其他类型普通商品，这一步将完成公式中的：“-工序库存量-资材库存量”
    List[no][1] = List[no][1] - mi
    fNeed = List[no][1]
    # 下面将完成公式中的：“（父物料的需求数量*子物料的构成数）/(1-损耗率)“
    for cNo in child[no]:
        cName = List[cNo][0]
        sql4 = "SELECT `损耗率`FROM `db_物料表` WHERE 名称=%s"
        cur.execute(sql4, cName)
        loss = cur.fetchall()[0][0]
        sql5 = "SELECT `构成数` FROM `db_调配构成表` WHERE `父物料名称`=%s AND `子物料名称`=%s"
        cur.execute(sql5, (name, cName))
        cNumber = cur.fetchall()[0][0]
        # 手根据父物料实际所需生产量来计算子物料的实际所需生产量
        List[cNo][1] = math.ceil(fNeed * cNumber / (1.0 - loss))


# --------------------------计算实际所需要的库存---------------------------
def solve1():
    # 批次靠前，并且下达命令时间早的先调用库存
    sList = sorted(List, key=lambda x: (-x[5], x[2]))
    print(sList)
    for item in sList:
        # 节点的编号
        no = item[3]
        # 计算实际所需生产量
        rQuantity(no)
    print(List)
    # 按照时间的早晚排序，输出相应的结果
    sList2 = sorted(List, key=lambda x: x[2])
    for i, pList in enumerate(sList2):
        pName = pList[0]
        pNeed = pList[1]
        pp = pList[4]
        sql6 = "SELECT `作业提前期`+`配料提前期`+`供应商提前期` AS pre_time FROM `db_库存表` a,`db_物料表` b,`db_调配构成表` c WHERE a.`物料号`=b.`物料号` AND a.`物料号`=c.`子物料号` AND `子物料名称`=%s"
        cur.execute(sql6, pName)
        # days表示持续时间，用于计算结束时间
        days = cur.fetchone()[0]
        sql7 = "SELECT `调配方式` FROM `db_物料表`WHERE 名称=%s"
        cur.execute(sql7, pName)
        method = cur.fetchone()[0]
        bListbox.insert(i,
                        f"{pp}     {pName}    {method}    {pNeed}   {pList[2]}   {pList[2] + datetime.timedelta(days)}")
    List.clear()


# --------------------------根据输入参数找到对应变量---------------------------
def solve2():
    varList = input.get().split()
    # print(nameList)
    for var in varList:
        sql8 = "SELECT `变量名` FROM `db_资产负债表` WHERE `资产类汇总序号`=(SELECT `序号` FROM `db_资产负债表` WHERE `变量名`=%s)"
        cur.execute(sql8, var)
        vName = cur.fetchall()
        cListbox.insert('end', f"{var} 等于如下参数的加和 :  ", vName)


# --------------------------创建GUI界面---------------------------
root = tkinter.Tk()
root.title("ERP实验-20000370")
root.geometry("700x700")
# 输入所需要生产的商品
tkinter.Label(root, text="product").place(x=60, y=10, width=150, height=30)
product = tkinter.Entry(root)
product.place(x=60, y=50, width=150, height=20)
# 输入所需要生产的商品数量
tkinter.Label(root, text="quantity").place(x=260, y=10, width=150, height=30)
quantity = tkinter.Entry(root)
quantity.place(x=260, y=50, width=150, height=20)
# 输入商品的要求完工时间
tkinter.Label(root, text="deadline").place(x=460, y=10, width=150, height=30)
deadline = tkinter.Entry(root)
deadline.place(x=460, y=50, width=150, height=20)
# 设置add,ok按钮
tkinter.Button(root, text="add", command=add).place(x=200, y=80, width=70, height=30)
tkinter.Button(root, text="ok", command=solve1).place(x=400, y=80, width=70, height=30)
# 设置显示框
aListbox = tkinter.Listbox(root)
aListbox.place(x=60, y=120, width=550, height=50)
tkinter.Label(root, text="plan").place(x=250, y=170, width=150, height=30)
bListbox = tkinter.Listbox(root)
bListbox.place(x=60, y=200, width=550, height=240)
# 设置退出按钮
tkinter.Button(root, text='exit', command=lambda: root.destroy()).place(x=320, y=650, width=40, height=30)
# 输入变量
tkinter.Label(root, text="variable ").place(x=270, y=440, width=150, height=30)
input = tkinter.Entry(root)
input.place(x=270, y=470, width=150, height=20)
# 设置按钮ok
tkinter.Button(root, text="ok", command=solve2).place(x=300, y=500, width=80, height=30)
# 设置显示框
cListbox = tkinter.Listbox(root)
cListbox.place(x=60, y=540, width=590, height=100)
# 进入消息循环
root.mainloop()
