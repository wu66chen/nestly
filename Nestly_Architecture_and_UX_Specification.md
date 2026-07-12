# Nestly 核心架构与商业级 UX 设计规范 (v1.0)

## 1. 宏观产品愿景与原则
Nestly 是一款自托管的专业级个人物品与空间管理系统。
* **核心理念**：数据表（理性结构）与 无限画布（空间直觉）的双向实时同步。
* **设计语言**：极致克制、高信噪比、毛玻璃质感（Glassmorphism）、Figma 级别的画布交互流畅度。
* **复刻原则**：所有端（Web/Mac/Win）必须严格遵循单一数据源（SSOT）渲染，绝不允许状态撕裂。

---

## 2. 空间层级与数据模型 (Data Model)
系统采用 **4级严格树状空间拓扑** 与 **扁平物品表** 组合的模型。

### 2.1 空间节点 (Nodes)
* **层级深度**：1级（房间） → 2级（位置） → 3级（容器） → 4级（子容器）。
* **数据结构**：`{ id, name, type, parentId, x, y, width, height, locked }`
* **约束**：不可跨级强制绑定，但允许物品挂载在任意层级（如物品直接放在“房间”的地板上）。

### 2.2 物品实体 (Items)
* **数据结构**：`{ id, item_code, name, category, status, location_id, quantity, notes, image, locked, x, y, sort_order, extra:{...} }`
* **唯一标识**：`item_code` 采用前缀自动递增策略（如 `ITM-0054`），删除补位，永久唯一。
* **坐标机制**：当 `location_id` 为空时，使用自身的 `x, y`（游离状态）；当被放入容器时，自身的 `x, y` 废弃，由 `location_id` 和 `sort_order` 通过网格引擎动态演算绝对坐标（Absolute Position）。

---

## 3. Z-Index 视觉层级体系 (Z-Axis Topology)
为了彻底解决窗口遮挡与层级穿透问题，UI 的 Z 轴高度被严格定义为以下常量级（客户端复刻时需映射为系统的 Window Level 或 Z-Order）：

| 元素 / 组件 | Z-Index / 深度 | 交互规则 |
|---|---|---|
| **图片灯箱 (Lightbox)** | `9999` | 最高模态框，全屏黑色半透明遮罩 (`rgba(0,0,0,0.85)`) |
| **右键菜单 (Ctx Menu)** | `999` | 绝对定位，点击空白处自动销毁 |
| **富文本模态窗 (RT Modal)** | `9998` | 遮罩 `rgba(0,0,0,0.3)`，包含编辑区与详情展开面板 |
| **视图切换器 (View Switcher)** | `999 !important` | 顶部居中，毛玻璃胶囊，**永远浮在数据表上方** |
| **固定工具栏 (Fixed UI)** | `30` | 包含撤销重做、交互手册按钮 |
| **数据表面板 (Side Panel)** | `10` | 抽屉式右侧面板，展开时遮盖底层按钮 |
| **面板收展按钮 (Toggle)** | `6` | 紧贴面板外侧，被面板自身遮挡，且必须低于 View Switcher |
| **Konva 画布顶层 (TopLayer)** | Canvas Top | 包含选中框、缩放锚点 |
| **Konva 胶囊层 (CapLayer)** | Canvas Mid-Top | 节点名称标签 |
| **Konva 物品层 (ItemLayer)** | Canvas Mid | 所有物品卡片 |
| **Konva 节点层 (NodeLayer)** | Canvas Mid-Bottom | 所有层级容器矩形 |
| **Konva 背景层 (BgLayer)** | Canvas Bottom | 点阵网格，`listening: false`（禁用事件透传） |

---

## 4. UI 视觉规范 (UI/UX Blueprint)

### 4.1 视图切换胶囊 (The Pill Switcher)
* **定位**：`top: 16px; left: 50%; transform: translateX(-50%);`
* **容器外观**：`background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); border-radius: 10px; padding: 4px; box-shadow: 0 4px 12px -2px rgba(0,0,0,0.1); border: 1px solid #e2e8f0;`
* **Tab 默认态**：`padding: 6px 14px; font-size: 13px; color: #64748b; border-radius: 6px;`
* **Tab Hover态**：`color: #1e293b;`
* **Tab 选中态**：`background: #eff6ff; color: #3b82f6; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05);`

### 4.2 数据表引擎 (Data Table Engine)
* **最小宽度防溢出**：面板最小宽度 `540px`。表格使用 `table-layout: auto` 配合 `word-break: break-all; overflow-wrap: anywhere`。极致缩窄时，文字必须自动折行，绝不允许被容器边缘硬性截断。
* **表头设计**：使用 `position: sticky; top: 0`。文字置于 `contenteditable` 容器中，双击可直接更改列名并持久化 (`localStorage`)。
* **富文本呼出**：单元格输入框聚焦 (`onfocus`) 时，右侧浮现蓝色 `✎` 按钮。点击弹出 `520px` 宽的富文本大输入窗。
* **飞书式详情面板**：点击操作列的 `⋯`，弹出单条记录全维度详情模态窗（纵向表单排列），支持无限追加自定义字段（Extra JSON）。
* **防手误删除**：点击 `✖` 后，按钮变为红色警告色并显示“确认删除”，3秒内未二次点击则自动恢复原状。

### 4.3 抽屉式收展逻辑 (Drawer Logic)
* **展开状态**：面板吸附右侧，记录并保持用户最后一次拖拽的宽度。
* **收起动作**：面板向右滑动出屏幕，仅保留 `8px` 露出边缘（`right: calc(-30% + 8px)`）。
* **跟随箭头**：收展按钮绝对计算相对位置，紧贴面板左外侧 `36px` 处。

---

## 5. 无限画布引擎设计 (Canvas Engine Architecture)

客户端复刻时，此部分逻辑必须严格一比一翻译，否则会导致性能崩溃或坐标错乱。

### 5.1 基础视口与渲染环境
* **HiDPI 优化**：必须强制 `PixelRatio = 1`。否则在 Retina 屏幕上由于嵌套层级和图形数量，GPU 填充率会几何级暴增导致卡顿。
* **背景防重绘**：绝不可使用 CSS Background 构建网格。必须使用 Canvas 内置的 `fillPatternImage`（20x20 离屏 Canvas 画圆点）铺满背景，随 Stage 自然缩放平移，达到零计算开销。

### 5.2 物品卡片设计 (160x64 Item Card)
* **尺寸**：固定 `width: 160, height: 64`，圆角 `6px`。
* **图片区**：左侧 `48x48` 区域。图片采用 **Proportional Cover Fit** 算法（`scale = Math.max(48/w, 48/h)`，居中裁剪），不拉伸。
* **图片异步加载队列**：绝不可以在渲染循环中逐个加载。需维护 `_imgFetching` 队列，图片完全加载后静默替换底图，全队列完成后 debounce (100ms) 统一触发 `batchDraw`，杜绝瀑布式卡顿。

### 5.3 智能 LOD (Level of Detail) 视口演算法
* **触发阈值**：当 `Stage.scale < 0.4` 时。
* **实时演化 (Live Transition)**：必须挂载于 `Wheel` (滚轮) 事件的 `requestAnimationFrame` 帧内计算。
* **详细态 (>0.4)**：显示全尺寸卡片、图片、名称、白底卡片、蓝色描边。
* **简易态 (<0.4)**：隐藏卡片底板与图片。仅在卡片中心点渲染一个大状态圆点 (`radius:10`)，底部挂载 `item_code`。极度缩小时只看颜色矩阵。

### 5.4 跑马灯算法 (Marquee Text Engine)
* **触发条件**：当前**仅选中一个**物品，且该物品名称**字符数 > 7**。取消选中立即停转归位。
* **视区裁剪机制**：绝不能用 DOM 的 CSS 实现。必须在 Canvas Text 节点上挂载 `clipFunc`。
    * **核心公式**：文字容器总宽为 `tw`，截断视窗宽为 `90px`。
    * `t = (Date.now() / 1000 * 18) % (tw - 90 + 40)`
    * `x = 64 - t`
    * `clipRect(64 - x, 0, 90, 16)` (使用相对反向坐标对冲 x 的移动)。

### 5.5 空间节点变形防扭曲系统 (Distortion-Free Resize)
**（极度重要：Figma 级缩放机制）**
* 传统 Canvas 的 `Group.scale` 会导致内部所有子元素变形（文字拉长，圆角变椭圆）。
* **Nestly 方案**：禁用底层 Transform Scale。自己绘制四个顶角锚点 (tl, tr, bl, br)。拖拽锚点时，**只改变节点的基础 `width` 和 `height` 属性，并将 `scale` 永远锁定为 1**。
* **圆角自适应公式**：`CornerRadius = Math.min(16, Math.max(4, Math.min(width, height) * 0.04))`。

### 5.6 挤位与网格吸附引擎 (Grid Snap & Reflow)
* **拖动中 (Drag Move)**：自由无阻尼跟随鼠标。仅在鼠标悬停于新容器上方 > 200ms 后，触发底层数据的 `sort_order` 重算。
* **松开时 (Drag End)**：
    * 游离物品：坐标就近吸附到 20px 步长的网格 (`Math.round(val / 20) * 20`)。
    * 容器内物品：计算相对父容器的局部坐标 `relX, relY`，转译为列数和行数，吸附到固定 168x72 的卡槽坑位中。

---

## 6. 数据双向绑定与刷新机制 (Sync Engine)
* **Single Source of Truth**：所有的操作（拖拽、表格改名、移动嵌套）必须第一时间修改内部的 `State (this.st)`。
* **节流渲染 (Debounce Render)**：
    * 画布重绘：使用 `requestAnimationFrame` 阻断同一帧内的多次 `sync()` 调用。
    * 表格 DOM 更新：使用 `setTimeout(..., 150)` 防止高频操作引发 DOM 卡顿。
* **初始防闪屏 (Anti-Flicker)**：初始化时，画布容器 `<div id="konva-container">` 与表格 `<tbody>` 必须默认 `visibility: hidden`。只有当数据加载完成、坐标落位、以及 `localStorage` 中记录的最后一次视角坐标 (`stageX, stageY, scale`) 恢复后，再移除隐藏类，实现完美的第一帧呈现。

---

## 7. 实体状态机 (State Machine)
### 锁定状态 (Locked = true)
通过右键菜单激活：
1. `item.locked = true` / `node.locked = true` 写入数据库。
2. 表格行渲染红色 🔒 按钮，卡片右下角渲染 🔒 Icon。
3. **禁用级**：点击无法选中（Selection Bypassed）；拖拽强制触发 `e.target.stopDrag()`；画布上屏蔽框选事件。
4. **联动级**：尽管自身被锁定，但如果其父容器被移动，它**必须被动跟随父容器改变绝对坐标**。

---

## 附录：跨平台端复刻指示 (For Client Agents)
如果你是负责移植 C++ / Swift / C# 版本的 Agent，请注意：
1. **摒弃原生缩放系统**：无论是 QGraphicsView 还是 CoreAnimation，不要用原生的 Group Scale 去缩放房间（节点）。必须像 5.5 节那样，拦截事件手动改尺寸再重绘圆角矩形，否则你的视觉 100% 崩塌。
2. **绝对坐标演算**：物品挂载入容器后，逻辑上必须剥离“父子渲染树”。物品的渲染坐标必须是 `Parent.GlobalX + Local OffsetX`。如果在树结构下强渲染，遇到极端缩放或边界裁切时会极难处理跑马灯和 LOD。
3. **文本排版边界**：表头的自动折行在不同系统上的测量宽度不同，计算面板最窄允许宽度（本案设为 540px）时，要依据所用 GUI 框架的文本度量 API 给足弹性安全距。