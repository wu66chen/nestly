# Nestly 商业级架构、API 与 UI/UX 蓝皮书 (Blueprint) v2.0

> **文档目标**：作为最高权威规范，指导 Web/macOS/Windows 多端客户端的 99.0% 像素级与交互级完美复刻。文档涵盖设计令牌、数据库架构、API 契约、状态机流转及画布核心算法。

---

## 1. 架构总览 (Architecture Overview)

Nestly 采用 **B/S 架构**与**厚前端（Thick Client）**模式。
* **后端 (Backend)**：Python Flask 负责持久化存储与附件IO，提供极简 REST API。业务逻辑极轻量。
* **数据库 (Database)**：SQLite 单文件存储，完全扁平化设计。
* **前端 (Frontend)**：Vanilla JS 驱动的单页应用（SPA）。状态由内存中的 State 对象托管。
* **渲染引擎 (Rendering)**：DOM 处理传统表单/UI，Konva.js (Canvas 2D API) 负责高性能无限画布渲染。双引擎通过数据状态机 (State Machine) 强同步。

---

## 2. 数据字典与 API 契约 (Data & API)

### 2.1 SQLite 数据库架构 (Schema)
全部依赖扁平表，通过 `parent_id` 和 `location_id` 实现无限层级。

* **`nodes` 表** (空间节点)
  * `id` (TEXT, PK): 唯一标识 (如 `id_xxxxx`)
  * `name` (TEXT): 节点名称
  * `type` (TEXT): `房间` | `位置` | `容器` | `子容器`
  * `parent_id` (TEXT, FK): 父节点ID（可为空）
  * `x`, `y`, `width`, `height` (REAL): 基础坐标与尺寸（Scale 永远为 1）
  * `locked` (BOOLEAN): 锁定状态

* **`items` 表** (物品实体)
  * `id` (TEXT, PK): 唯一标识
  * `item_code` (TEXT): 永久业务编码 (如 `ITM-0054`)，删除补位
  * `name`, `category`, `status` (TEXT): 基础属性
  * `location_id` (TEXT, FK): 所在节点ID（可为空，为空时为游离态）
  * `quantity` (INTEGER): 数量
  * `notes` (TEXT): 备注
  * `image` (TEXT): 图片文件名
  * `locked` (BOOLEAN): 锁定状态
  * `x`, `y` (REAL): 游离态坐标
  * `sort_order` (INTEGER): 容器内排序（决定网格坑位）
  * `extra` (JSON TEXT): 动态扩展字段键值对

### 2.2 REST API 契约
* `GET /api/state` -> `{ nodes: [...], items: [...] }` (全量拉取)
* `POST /api/state` <- `{ nodes: [...], items: [...] }` (全量覆盖，Debounce: 800ms)
* `POST /api/upload/<item_id>` -> FormData(`image`) -> 返回 `{ success: true, image: 'filename.jpg' }`

---

## 3. 设计令牌与视觉规范 (Design Tokens)

任何端复刻必须严格采用以下参数，以保证毛玻璃与克制感的高级视觉语言。

### 3.1 颜色系统 (Color Palette)
* **品牌色 (Primary)**: `#3b82f6` (Blue 500)
* **背景底色 (Background)**: `#fafbfc`
* **点阵颜色 (Dots)**: `#cbd5e1`
* **文字主色 (Text Primary)**: `#1e293b` (Slate 800)
* **文字辅色 (Text Secondary)**: `#64748b` (Slate 500)
* **边框色 (Border)**: `#e2e8f0` (Slate 200)
* **成功/常用态 (Success)**: `#22c55e` (Bg), `#166534` (Text)
* **警告/闲置态 (Warning)**: `#ef4444` (Bg), `#dc2626` (Text)

### 3.2 节点样式矩阵 (Node Styles Matrix)
| 层级 | 默认尺寸 | 描边颜色 | 描边宽度 | 胶囊背景 | 胶囊文字 |
|---|---|---|---|---|---|
| 1. 房间 | 600x400 | `#94a3b8` | 2px | `#e2e8f0` | `#334155` |
| 2. 位置 | 400x280 | `#93c5fd` | 1.5px | `#dbeafe` | `#1e40af` |
| 3. 容器 | 240x180 | `#fde047` | 1px | `#fef08a` | `#854d0e` |
| 4. 子容器 | 160x100 | `#86efac` | 1px | `#dcfce7` | `#166534` |

### 3.3 Z-Index 拓扑结构 (Z-Order Topology)
| Z-Index | UI 组件 | 说明 |
|---|---|---|
| `9999` | Lightbox (灯箱) / CtxMenu (右键菜单) | 全局最高层 |
| `9998` | RT Modal (富文本/详情模态窗) | 遮盖常规UI，仅低于灯箱 |
| `999 !important` | View Switcher (视图切换胶囊) | 必须永远漂浮在数据表面板上方 |
| `30` | Toolbar (左上工具栏) | 独立于面板的悬浮控件 |
| `10` | Side Panel (数据表面板) | 主交互区，背景 `blur(12px)` |
| `6` | Panel Toggle (收展箭头) | 紧贴面板左外侧，被面板自身遮挡 |

---

## 4. 核心组件交互算法 (Core Interactions & Algorithms)

### 4.1 数据表面板抽屉算法 (Drawer Panel)
* **动画曲线**：`transition: right 0.4s cubic-bezier(0.16, 1, 0.3, 1)`（Apple 级平滑阻尼弹性曲线）。
* **展开逻辑**：恢复到保存在内存中的 `_savedPanelW`，最小极限宽 `540px`。
* **收起逻辑**：设置 CSS `right: calc(-30% + 8px)`，让面板退至屏幕外，仅留 `8px` 阴影边界提示存在感。
* **箭头跟随**：由于 CSS `calc` 在拖拽 resize 时的滞后性，箭头必须使用 JS 实时计算：`tg.style.left = (panel.getBoundingClientRect().left - 36) + 'px'`。

### 4.2 无限画布渲染管线 (Canvas Render Pipeline)
* **防锯齿与 GPU 填充率控制**：强制 `Konva.pixelRatio = 1`。禁用 Retina 的物理像素翻倍，将渲染负载降低 75%，保证万件物品不卡顿。
* **分层策略 (Layering)**：
  1. `bgL`: 点阵背景，`fillPatternImage`（离屏 20x20 Canvas），`listening: false`。
  2. `nL`: 节点矩形。
  3. `iL`: 物品卡片。
  4. `cL`: 节点胶囊名牌。
  5. `tL`: 选中框、缩放锚点，独占顶层确保永远可交互。
* **节流渲染 (Debounce Sync)**：所有的状态修改（位置、名字）均调用 `this.sync()`。`sync()` 内部通过 `requestAnimationFrame` 防抖，确保一帧内发生的 100 次修改只触发 1 次 `_doSync()` 重绘。

### 4.3 智能 LOD 演算法 (Level of Detail)
监听 `wheel` 事件中的 `Stage.scale` (设为 `ns`)。
* **触发边界**：`ns < 0.4`。
* **响应方式**：无需等待 `sync()` 完整重构。在 `wheel` 回调中直接通过 `requestAnimationFrame` 遍历 `iL`：
  * **详细态 (ns >= 0.4)**：卡片底板 (`.base`)、图片 (`.imgGroup`)、名称 (`.tName`) 设为 `visible: true`。中心大绿点 (`.lodDot`) 设为 `false`。
  * **简易态 (ns < 0.4)**：隐藏卡片底板与图片细节。中心大绿点设为 `visible: true`，显示状态颜色。文字仅保留底部的 `item_code`。
* **性能收益**：缩放时免去了复杂的裁剪计算与阴影绘制。

### 4.4 变形防扭曲系统 (Distortion-Free Resize)
原生图形引擎的坑：对 Group 进行 Scale 会拉伸文本，并将圆角变成椭圆。
* **Nestly 解法**：完全禁用 `Transformer`，自行实现 4 角 `Circle` 锚点。
* **拖拽锚点公式**：
  * 右下角 (`br`) 拖拽改 `width, height`：`nw = startW + dx`, `nh = startH + dy`。
  * 左上角 (`tl`) 拖拽改 `x, y, width, height`：`nw = startW - dx`, `nx = startX + dx`。
* **重绘下发**：将算出的真实宽高直接赋给底部的 `Rect`，并实时应用公式 `cornerRadius = Math.min(16, Math.max(4, Math.min(nw, nh) * 0.04))`。子元素永远在 `Scale=1` 的环境中被重绘，实现 Figma 级尺寸调整。

### 4.5 相对坐标解算与网格挤位 (Grid Snapping)
物品一旦绑定到 `location_id`，其自身的 `x, y` 失效。
* **拖拽吸附逻辑**：
  拖动物品至某节点上方，利用反向矩阵计算局部坐标：
  `rel = parentGroup.getAbsoluteTransform().copy().invert().point(pointerPosition)`
* **坑位计算**：
  `cols = Math.max(1, Math.floor((parentWidth - 24 + 8) / 168))`
  `col = Math.round((rel.x - 12) / 168)`
  `row = Math.round((rel.y - 40) / 72)`
  `slot = row * cols + col`
* **挤位重排 (Reflow)**：
  鼠标悬停在 `slot` 上方静置 > `200ms`，触发数组插入：从原数组剔除该物品，并在 `slot` 索引处 `splice` 插入，重算所有同级兄弟的 `sort_order`，下发重绘。

### 4.6 跑马灯视窗算法 (Marquee Text Engine)
* **激活条件**：选中唯一卡片 (`this.sel.length === 1`) 且文本长度 > 7。
* **时间函数**：基于 `Date.now()` 的数学取模，彻底摒弃 CSS Animation 带来的渲染树污染。
  `const tw = textWidth; const dist = tw - 90 + 40;`
  `const t = (Date.now() / 1000 * 18) % dist; // speed = 18`
  `textNode.x(64 - t);`
* **像素裁剪**：在 Text 节点直接挂载 `clipFunc`：
  `ctx.rect(64 - textNode.x(), 0, 90, 16);` （使用反向偏移抵消自身移动，保证裁剪窗口相对于卡片永远静止在 `[64, 0]`）。

---

## 5. 跨平台端移植避坑指南 (Porting Guidelines)

1. **禁用任何 GUI 框架的原生 Scale 组**：无论是 Qt (C++)、WPF (C#) 还是 SwiftUI，在实现容器缩放时，**严禁**使用其自带的视图缩放包裹器缩放容器组，必须拦截手势并转化为基础的 `Width/Height` 属性更改。
2. **文本自动换行与度量**：在数据表面板极窄状态 (540px) 时，如果底层 UI 框架不支持 `break-all`（任意字符强行断行），请通过计算列宽手动插入换行符，绝对不允许文本被容器外边缘裁切。
3. **高频事件防抖**：`Wheel` (缩放)、`MouseMove` (拖拽) 均为硬件级高频事件 (可达 1000Hz+)。所有视觉变更（如更新锚点位置、更新胶囊位置）必须利用操作系统的垂直同步（如 `requestAnimationFrame` / `DisplayLink` / `CompositionTarget`）进行降频，避免主线程锁死。
4. **单向数据流与游离态**：注意处理 `items` 的坐标。当物品从一个容器被拖离并松开在空白处时，需立刻使用 `parent.invert().point(absolutePos)` 解算它脱离前的绝对屏幕坐标，并写入其自身的 `x, y`，同时清除 `location_id`。这样它落下的瞬间在视觉上才不会发生跳跃。