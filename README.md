# Nestly

> 无限画布 · 层级空间 · 专业级交互

一个自托管的个人物品整理工具。通过**数据表录入** + **画布可视化**，以 4 级层级结构（房间 → 位置 → 容器 → 子容器）管理物品，支持拖拽、缩放、锁定、网格吸附等专业画布操作。

## 截图

![screenshot](https://via.placeholder.com/800x500/f8fafc/64748b?text=Nestly+Screenshot)

## 功能

### 数据管理
- 物品 CRUD（编号自动生成、永久绑定、删除后补位）
- 12 列数据表：图片、编号、名称、分类、房间、位置、容器、子容器、状态、数量、备注
- 筛选 & 8 种双向排序（编号降序/升序、最新创建、名称 A-Z/Z-A、数量排序）
- 表头可自由重命名
- 数据自动保存到 SQLite / JSON API

> **核心亮点：数据表 ↔ 画布 双向实时联动**
>
> 表格修改任意字段（名称、层级、锁定状态）→ 画布瞬间同步。画布拖拽/缩放对象 → 坐标和状态自动回写数据表。两者始终同源，不新建、不复写、不丢数据。

### 画布（无限画布）
- 4 级层级空间可视化（房间 → 位置 → 容器 → 子容器）
- 物品卡片 160×64px，含图片、编号、名称、状态标识
- 空间 / 中键平移 · 滚轮缩放 · 框选多选
- Shift + 点击切换多选 · Ctrl+Z / Ctrl+Shift+Z 撤销重做
- 自定义四角锚点缩放矩形（内部对象永不变形）
- 物品拖拽自由移动，松手后网格吸附
- 对象锁定（右键菜单）：锁定后不可选中/拖拽，但仍跟随父容器移动
- 胶囊标签始终紧贴矩形左上角外侧，缩放不变形
- 自适应 LOD 显示（缩小时隐藏细节）

### 部署
- Docker 一键部署
- 数据持久化（Docker volume）
- 支持 NAS 极空间 / Synology / 任意 Linux

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vanilla JS + Konva.js 9 + Tailwind CSS (CDN) |
| 后端 | Python Flask + SQLite |
| 部署 | Docker + docker-compose |
| 性能优化 | `Konva.pixelRatio=1`、clipFunc 闭包、rAF 节流、Konva `fillPattern` 点阵、CSS → Canvas 全 GPU 渲染 |

## 快速开始

### Docker 部署

```bash
# 克隆仓库
git clone https://github.com/wu66chen/nestly.git
cd nestly

# 启动
docker compose up -d

# 访问 http://localhost:8089
```

### NAS 极空间部署

```bash
# 将文件上传到 NAS
scp -r ./* user@nas-ip:/tmp/zfuse/docker/nestly/

# SSH 到 NAS 执行
ssh user@nas-ip
cd /tmp/zfuse/docker/nestly
sg docker -c 'docker compose up -d'
```

## 热更新

修改前端代码后无需重建镜像：

```bash
# 编码并上传
cat templates/index.html | base64 > /tmp/index.b64
ssh user@nas-ip "base64 -d > /tmp/zfuse/docker/nestly/templates/index.html"
ssh user@nas-ip "sg docker -c 'docker cp /tmp/zfuse/docker/nestly/templates/index.html nestly:/app/templates/index.html && docker restart nestly'"
```

## 交互手册

| 操作 | 方式 |
|------|------|
| 平移视图 | 空格 + 左键拖拽 / 中键拖拽 |
| 缩放视图 | 滚轮 |
| 框选多选 | 空白处拖拽 |
| Shift 多选 | Shift + 点击对象 |
| 撤销 / 重做 | Ctrl+Z / Ctrl+Shift+Z |
| 删除选中 | Backspace / Delete |
| 缩放矩形 | 选中矩形后拖拽四角蓝色锚点 |
| 锁定对象 | 右键对象 → 🔒 锁定 |
| 原位编辑 | 双击胶囊标签 |

## 文件结构

```
nestly/
├── app.py              # Flask 后端 (API + SQLite)
├── templates/
│   └── index.html      # 前端 (Konva.js 画布 + 数据表)
├── static/             # 静态文件 (CSS/JS 可选)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```
