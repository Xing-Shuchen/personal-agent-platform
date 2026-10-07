专员办公室（OpenClaw Agent Office Floor）技术规格书

规格版本：0.9
核验基准：2026-10-03
交付形态：本地 HTTP 服务提供的浏览器应用，通过 OpenClaw portal 展示。


本规格依据 Munder Difflin（下称 MD）的公开源码、OpenClaw 官方文档及协议定义制定。上游 main 分支不作为可复现版本标识；开发启动前必须固定 MD 提交 SHA、OpenClaw Gateway 版本及客户端依赖版本。目标机器的实际版本、权限和事件载荷尚未实测，相关事项以 【待验证】 标明。

文中“必须”“不得”为验收要求；轮询间隔、重试次数、容量和延迟指标均为本项目约定，不是对上游默认行为的描述。

⸻

一、范围与非目标

1.1 产品范围

专员办公室是 OpenClaw 会话的只读可视化观察面。

一个纳入展示范围的会话对应一个小人。用户能够通过名字、动作、状态字形和中文标签，区分谁正在运行、谁需要输入、谁发生错误、谁最近完成了一轮工作，以及哪些状态已经失去实时依据。

范围	必须提供的能力
办公室场景	2D 像素地图、专员小人、座位、显示器、相机和状态气泡
实时状态	优先消费 Gateway 订阅事件；不可订阅时使用明确标识的轮询模式
专员身份	稳定绑定会话与外观；同一 agentId 的多个会话不得合并为一个小人
会话详情	可用时展示模型、用量、最近活动、运行标识、工作摘要和已有进度卡
异常可见性	明确区分“专员报错”“数据过期”“Gateway 离线”“权限不足”
浏览器交付	不依赖 Electron、桌面预加载桥或终端模拟器
数据源解耦	场景只接收 FloorState，能够用固定测试数据独立运行

MD 的原架构同时存在终端平面和 hook/hive 事件平面，并通过 window.cth 与渲染器通信。本项目只抽取办公室渲染能力，不迁移上述数据平面。

1.2 非目标

非目标	边界
多智能体编排	不创建、分配、唤醒、重试、暂停或终止 OpenClaw 会话
MD 进程层	不引入 hive、GOD、roster、PTY、hook、webhook、终端输出解析
会话操作台	MVP 不发送消息、不回答问题、不批准操作、不切换模型
自动生成进度	只读取已有进度；不得为了刷新界面触发智能体运行
推测性监控	不根据“很久没消息”“文本反复出现”“最近活动时间”判定卡住、循环或成功
全量聊天客户端	不保存或呈现完整聊天记录、工具参数、工具结果和隐藏推理内容
多用户共享平台	MVP 仅支持一个明确授权的观察者身份，不提供共享办公室链接或跨用户权限管理

“已完成”默认指最近一轮运行成功结束，不等于长期任务、进度卡、全部子任务或业务目标已经完成。

⸻

二、架构与数据流

2.1 总体架构

OpenClaw Gateway
  │
  │ Gateway WebSocket RPC、会话事件
  │ sessions.list / sessions.subscribe / sessions.messages.subscribe
  │ 必要时读取会话详情、历史运行快照、已有进度卡
  ▼
OpenClaw 数据源适配器〔本地服务端〕
  ├─ 认证与能力核验
  ├─ 会话身份、可见范围、运行关联
  ├─ 事件合并、快照校准、失败降级
  └─ 内容裁剪与脱敏
  │
  ▼
FloorState〔与 OpenClaw、Pixi 均无依赖的状态契约〕
  │
  │ 本项目 HTTP 快照接口 + SSE 增量接口
  ▼
浏览器宿主〔React〕
  ├─ 状态接收与校验
  ├─ 专员列表、详情、连接状态
  └─ 将 FloorState 注入场景库
        │
        ▼
      办公室场景库〔React + Pixi.js〕
        ├─ 状态 → 动画、字形、显示器
        ├─ 小人、座位、地图、相机
        └─ Canvas 呈现
portal：代理本地 HTTP 服务至控制台可访问的独立来源；
        不承担 OpenClaw 状态解析，也不代替应用自身的访问控制。

Gateway 官方提供 WebSocket 客户端协议、会话订阅和客户端 SDK，因此适配器不需要从 PTY 或日志模拟会话状态。浏览器与本地服务之间选择 SSE，是本项目的单向数据传输约定；OpenClaw portal 文档明确支持包括 SSE 在内的流式 HTTP 响应。

2.2 组件职责与依赖方向

组件	职责	允许依赖	禁止依赖
floor-contract	类型、状态版本、传输契约	基础 TypeScript 类型	React、Pixi、OpenClaw SDK、MD store
openclaw-adapter	Gateway 数据归一化	Gateway 客户端与协议包、契约	场景对象、DOM、MD 编排模块
本地 HTTP 服务	托管页面、输出快照和 SSE、控制访问	适配器、契约	智能体进程管理、通用 RPC 转发
浏览器宿主	接收状态、详情面板、展示配置	React、契约、场景库	Gateway 凭据、Node 原生模块
office-scene	地图和角色可视化	React、Pixi、契约、场景资源	Gateway SDK、MD store、window.cth、网络状态采集

场景库的唯一动态业务数据入口是 FloorState。主题资源、视觉设置和选择回调属于宿主配置，不得成为第二条会话数据通道。

2.3 本地服务接口

以下路径是本项目新增接口，不是 OpenClaw 原生 API。

接口	用途	约束
GET /api/floor/state	当前完整 FloorState	禁止缓存；经过应用访问检查
GET /api/floor/events	SSE，发送完整快照或增量	首条业务消息为快照；每 15 秒发送传输心跳
GET /healthz	服务存活检查	不返回会话名称、内容、密钥或 Gateway 地址
静态资源路径	页面、脚本、合法主题资源	与页面同源；不依赖第三方 CDN

浏览器不直接连接 Gateway。Gateway 设备身份、签名材料和令牌仅保存在服务端，不写入前端构建产物、浏览器存储、查询字符串或日志。

2.4 portal 交付约束

应用必须读取 PORT，在 Gateway 所在机器的回环地址监听；需要绝对 URL 时使用 PUBLIC_URL。页面资源和 SSE 优先使用同源相对路径。MVP 不涉及远程 worker 部署。portal 声明文件和打开 portal 的动作不等于自动启动应用服务。

portal 使用独立来源，代理认证也不等于应用获得了访问者的 OpenClaw 身份。本项目必须维持“一个获准观察者对应一个服务端数据视图”的边界，不得把高权限适配器读取的会话经共享链接暴露给其他人。实际控制台嵌入、来源限制和应用访问检查须在目标环境验收；不通过时仅允许本机访问，不得以公开暴露端口作为替代。

⸻

三、场景层抽取方案

3.1 采用方式

采用“选择性 vendor 源码进仓库，并封装为内部 workspace 包”。不 fork 整个应用，不在 MVP 发布公共 npm 包。

方案	结论	理由
选择性 vendor	采用	能逐文件保留来源、审查修改，并彻底排除 MD 的主进程和编排代码
fork 整个 MD	不采用	容易继续依赖 Electron 构建、安装脚本、store 和进程层
直接依赖上游 npm 场景包	不采用	当前核验的是 MD 应用源码，不是已验证的独立场景包
本项目内部 workspace 包	采用	为后续独立发布保留边界，但不提前承担公共包兼容性与美术分发问题

MD 的 package.json 包含 Electron 构建及原生模块安装流程，不能整体复制到新项目。只建立本项目实际需要的浏览器和服务端依赖。

vendor 记录必须包含：上游仓库、提交 SHA、原始路径、许可证、文件校验值和本地修改说明。升级必须通过同一组视觉、契约和依赖边界测试，不允许无审查同步整个目录。

3.2 必须纠正的实现假设

项目	核验结果	本项目处理
角色尺寸和生成路径	当前 cast.ts 调用 portraitArt.ts 程序化生成场景帧；场景尺寸是 18×32	不把整个角色系统固定为 16×32；以生成器尺寸和脚底锚点为准
SpriteAdapter.ts 的位置	它是外部人物 sheet 的兼容适配器；16×32、每方向 6 帧属于该输入配置	保留为可选兼容模块，不作为现有人物生成管线的必经路径
三行七帧	当前程序化帧仍提供三行七帧；侧面行复用正面，左向水平翻转	不宣称具备独立的完整四方向人物美术
打字和阅读动画	CharacterSprite.ts 的 walk/type/read 当前都使用 [0,1,2,1]，主要区别在速度和场景姿态	MVP 保留枚举，通过状态文字、座位和显示器增强辨识；独立动作帧属于后续美术增强

上述差异分别可在 cast.ts、portraitArt.ts、SpriteAdapter.ts 和 CharacterSprite.ts 中核实，不能以旧注释替代实际执行路径。

3.3 逐模块抽取与解耦

下表中未写完整前缀的路径均相对于 MD 的 src/renderer/src/scene/office/。

原模块	处理方式	必须修改的耦合或行为
OfficeFloor.tsx	保留场景组织和 Pixi 生命周期，重写数据接入	删除 useStore、MD Agent 类型；由宿主注入 FloorState；角色集合按稳定 ID 增删更新
Character.ts	保留移动、落座、字形、名牌等能力	参数中的 agent 身份改为场景实体 ID；点击改为宿主回调；不得自行解释 OpenClaw 状态
CharacterSprite.ts	保留帧播放与坐姿裁剪	维持四种动画枚举；纹理尺寸不写死；完成动效不得因无关状态更新重复触发
SpriteAdapter.ts	作为可选模块保留	输入资源必须显式提供配置及授权来源；不重新引入已删除的第三方人物 sheet
cast.ts、portraitArt.ts	作为默认人物生成管线	外观 ID 与会话名称分离；缓存按外观配方及版本管理；新增原创专员配方
themeRegistry.ts	拆分主题元数据与资源地址	删除 @/assets/... 静态绑定；由本地主题清单提供地图、图集、座位、屏幕 GID 和资源根路径
themeLoader.ts	保留加载入口并加强验证	将“可解析 JSON”验证扩展到完整资源加载事务；不能只检查地图后就认为主题可用
TiledMapRenderer.ts	保留地图绘制、坐标和可行走信息	保持图层、firstgid、翻转标志、碰撞和出生点语义；地图不承担会话状态判断
DeskScreen.ts	保留 GID 覆盖和动画	屏幕开关由归一化工作状态决定，不再以“人物坐在桌前”作为开机依据
MessageEnvelope.ts	保留纯视觉对象，默认禁用业务触发	输入改为本项目已验证的通信事件；删除 hive 消息语义和演示事件依赖
ThoughtBubble.ts、ToolBubble.ts	保留气泡排版和图标能力	显示经裁剪的工作摘要、工具名和等待原因；不得显示隐藏推理或完整工具参数
pathfinding.ts、Camera.ts	保留	前者是基于网格的 BFS；相机跟随由宿主选择状态驱动，不依赖终端焦点
SeatPool.ts	纳入新的场景运行时	统一座位分配和释放；原 OfficeFloor.tsx 的内联座位管理必须实际迁移，不能只新增一个未使用的工具类
cafeteriaLines.ts	默认不启用	删除电视剧人物对白与 GOD 特例；未来启用时必须明确为装饰，不得冒充真实对话
glRecovery.ts	保留并修正生命周期边界	恢复只重建图形资源，不清空业务状态；跨重建保留重试预算，避免无限恢复
src/renderer/src/design/tokens.*	复制实际使用的 token 子集	改为场景内部导入；CSS 限定作用域；中文文字使用可用的系统字体回退

角色、地图、屏幕和气泡模块已有可复用的渲染边界；座位与场景行为仍需在 OfficeFloor.tsx 中重新组织。
寻路、相机、装饰对白、恢复和 token 的处理分别以上游对应文件为依据。

3.4 OfficeFloor.tsx 的额外耦合清理

仅替换 store import 不足以完成抽取。

已发现的耦合	必须采取的改法
window.cth.hiveTasks()	删除任务墙、完成统计、老板光环等对应调用；需要保留墙面时改为纯装饰
window.cth.onHiveMessage	删除；仅由 FloorState.handoffs 驱动信封
cth:demo-handoff 全局事件	从正式运行路径删除；演示只能存在于隔离测试环境
isGod、老板专座和特殊活动	删除业务身份特判；是否保留某个座位仅属于主题布局
MD command center 跳转	改为本地详情面板；不假定 OpenClaw 控制台深链接格式
终端全屏、IDE 开关影响渲染	改为浏览器页面可见性和组件挂载状态
根据工作持续时间、回到 idle 等条件庆祝	删除；仅在收到与当前会话实例关联的成功终态后触发
react-i18next 与全局语言状态	场景中文标签由本项目提供，不继承 MD 全局应用状态

这些入口存在于当前 OfficeFloor.tsx，包括真实 hive 消息和演示信封两条路径。

3.5 资源、CSP 与恢复策略

资源加载。 主题清单必须显式描述地图和图集，并保持 texture[i] 与 tilesets[i] 的对应关系。加载顺序为：地图解析 → 元数据检查 → 图集加载 → GID 和座位校验 → 场景提交。任一步失败都不得留下半初始化场景。MD 当前 loadTheme() 主要进行轻量地图检查，其回落行为不能直接视为已经覆盖图片缺失、网络失败或 GPU 初始化失败。

回落。 自定义主题失败时尝试已安装且授权有效的 office 主题一次；默认主题也不可用时，显示 DOM 专员状态列表和资源错误，不得白屏，也不得反复加载失败资源。

CSP。 不把 pixi.js/unsafe-eval 简化为“Electron 专用、浏览器可以直接删除”。Pixi 对应模块包含避免动态求值的兼容实现。本项目在浏览器初始化入口集中处理该兼容层，不允许通过放宽为 script-src 'unsafe-eval' 来解决问题。锁定版本是否需要保留该模块，须通过严格 CSP 下的真实构建测试决定。

图形恢复。 采用最多 3 次、间隔 1,500 毫秒的重建预算，与上游恢复模块的默认量级一致；预算归属于场景实例生命周期，而不是每次重新安装监听器。耗尽后停留在 DOM 列表，保留用户主动重试入口。

3.6 目录结构

agent-office-floor/
├─ apps/
│  ├─ web/                         浏览器入口、专员列表、详情面板
│  └─ server/                      HTTP、SSE、访问控制、静态文件托管
├─ packages/
│  ├─ floor-contract/
│  │  └─ src/                      FloorState、更新协议、校验契约
│  ├─ openclaw-adapter/
│  │  └─ src/
│  │     ├─ connection/            认证、能力检查、重连
│  │     ├─ sessions/              列表、身份、订阅、运行关联
│  │     ├─ normalization/         字段归一化、状态判定
│  │     └─ privacy/               裁剪、脱敏、可见范围
│  └─ office-scene/
│     ├─ UPSTREAM.md              来源、提交 SHA、原路径
│     ├─ PATCHES.md               本地修改及原因
│     └─ src/
│        ├─ index.ts              受控导出
│        ├─ scene/office/         抽取后的 MD 渲染模块
│        ├─ stateMapping/         FloorState → 视觉行为
│        ├─ themes/               主题契约、加载与校验
│        └─ design/               场景 token、局部样式
├─ assets/
│  ├─ owned/                      可随项目分发的原创资源
│  └─ licensed-local/             本机合法授权资源，不进入公开分发
├─ tests/
│  ├─ fixtures/                   脱敏 Gateway 事件及合成 FloorState
│  ├─ contract/                   快照、增量、身份和状态测试
│  └─ browser/                    视觉、CSP、恢复、portal 测试
└─ notices/                       MIT、ISC 来源及美术授权记录

⸻

四、FloorState 接口与更新语义

4.1 设计原则

FloorState 是可 JSON 序列化的不可变快照，不包含 Pixi 对象、React 对象、函数、Date、Map、Gateway 原始载荷或凭据。

业务状态与可观测性分开。 会话可以“最后确认正在运行，但数据已经过期”；不得把连接断开改写为会话失败，也不得继续用无提示的打字动画表示实时运行。

4.2 TypeScript 接口

以下为接口契约，不包含实现。

export type FloorId = string;
export type TimestampMs = number;
export type FloorStatus =
  | "running"
  | "waiting_input"
  | "error"
  | "completed"
  | "idle"
  | "queued"
  | "stopped"
  | "unknown";
export type WorkPhase =
  | "executing"
  | "reading"
  | "thinking"
  | "finishing"
  | "waiting_child"
  | null;
export type Freshness = "fresh" | "stale" | "unknown";
export type CapabilityState =
  | "available"
  | "partial"
  | "unsupported"
  | "forbidden"
  | "unverified";
export type CapabilityName =
  | "sessionList"
  | "sessionEvents"
  | "runEvents"
  | "toolEvents"
  | "blockingInput"
  | "progressCard"
  | "compaction"
  | "loopDetection"
  | "handoff";
export interface ObservationEvidence {
  readonly source:
    | "session_snapshot"
    | "session_delta"
    | "run_event"
    | "tool_event"
    | "input_event"
    | "operation_event"
    | "progress_card";
  readonly reference: string;
  readonly sourceAtMs: TimestampMs | null;
  readonly observedAtMs: TimestampMs;
}
export interface InputAttention {
  readonly id: string;
  readonly kind: "question" | "approval";
  readonly runId: string | null;
  readonly blocking: boolean | null;
  readonly label: string;
}
export interface RunOutcome {
  readonly runId: string | null;
  readonly result: "success" | "error" | "cancelled" | "timeout";
  readonly endedAtMs: TimestampMs | null;
  readonly message: string | null;
}
export interface FloorProgress {
  readonly revision: number;
  readonly updatedAtMs: TimestampMs;
  readonly markdown: string | null;
  readonly steps: readonly {
    readonly text: string;
    readonly status: "pending" | "in_progress" | "completed";
  }[] | null;
}
export interface FloorAgent {
  readonly id: FloorId;
  readonly session: {
    readonly gatewayId: string;
    readonly key: string;
    readonly agentId: string | null;
    readonly sessionId: string | null;
  };
  readonly name: string;
  readonly kind: string | null;
  readonly avatarKey: string;
  readonly relation: {
    readonly parentId: FloorId | null;
    readonly childIds: readonly FloorId[] | null;
    readonly runningVisibleChildren: number | null;
  };
  readonly work: {
    readonly status: FloorStatus;
    readonly phase: WorkPhase;
    readonly hasActiveRun: boolean | null;
    readonly activeRunIds: readonly string[] | null;
    readonly tool: {
      readonly name: string;
      readonly callId: string | null;
      readonly phase: "start" | "update" | "end";
    } | null;
    readonly attention: readonly InputAttention[] | null;
    readonly compacting: boolean | null;
    readonly looping: boolean | null;
    readonly latestOutcome: RunOutcome | null;
    readonly summary: string | null;
    readonly summarySource:
      | "tool"
      | "narration"
      | "progress_card"
      | "visible_message"
      | null;
    readonly evidence: readonly ObservationEvidence[];
  };
  readonly model: {
    readonly selected: string | null;
    readonly selectedProvider: string | null;
    readonly active: string | null;
    readonly activeProvider: string | null;
  };
  readonly usage: {
    readonly inputTokens: number | null;
    readonly outputTokens: number | null;
    readonly totalTokens: number | null;
    readonly totalTokensFresh: boolean | null;
    readonly contextTokens: number | null;
  };
  readonly progress: FloorProgress | null;
  readonly lastMessagePreview: string | null;
  readonly metadataUpdatedAtMs: TimestampMs | null;
  readonly lastActivityAtMs: TimestampMs | null;
  readonly lastInteractionAtMs: TimestampMs | null;
  readonly lastVerifiedAtMs: TimestampMs | null;
  readonly freshness: Freshness;
}
export interface FloorHandoff {
  readonly id: string;
  readonly fromId: FloorId;
  readonly toId: FloorId;
  readonly kind: "request" | "result" | "message";
  readonly observedAtMs: TimestampMs;
  readonly expiresAtMs: TimestampMs;
  readonly evidenceReference: string;
}
export interface FloorConnection {
  readonly mode: "subscription" | "polling" | "none";
  readonly state:
    | "connecting"
    | "live"
    | "degraded"
    | "offline"
    | "auth_required";
  readonly lastConfirmedAtMs: TimestampMs | null;
  readonly reason: string | null;
}
export interface FloorState {
  readonly schemaVersion: 1;
  readonly epoch: string;
  readonly revision: number;
  readonly generatedAtMs: TimestampMs;
  readonly connection: FloorConnection;
  readonly capabilities: Readonly<
    Record<CapabilityName, CapabilityState>
  >;
  readonly agents: Readonly<Record<FloorId, FloorAgent>>;
  readonly handoffs: readonly FloorHandoff[];
}
export type FloorUpdate =
  | {
      readonly type: "snapshot";
      readonly state: FloorState;
    }
  | {
      readonly type: "patch";
      readonly schemaVersion: 1;
      readonly epoch: string;
      readonly baseRevision: number;
      readonly revision: number;
      readonly generatedAtMs: TimestampMs;
      readonly upserts: readonly FloorAgent[];
      readonly removeIds: readonly FloorId[];
      readonly connection?: FloorConnection;
      readonly capabilities?: FloorState["capabilities"];
      readonly handoffs?: readonly FloorHandoff[];
    };

4.3 字段和空值语义

项目	规定
id	根据 Gateway 实例、经确认的会话所有者和原始会话 key 生成稳定、不碰撞的标识；不得使用数组下标或显示名称
sessionId	会话实例标识。相同 key 更换 sessionId 时，清空旧运行、等待、进度关联和临时效果；外观绑定可以保留
agentId: null	尚无可验证的所有者信息；若存在身份歧义，该行不得参与跨会话关联
kind	保留实际数据面的值；不得混用会话工具与 Gateway 行结构中不同的 kind 分类
null	未知、未提供或不可用，不等于零、空闲或没有
activeRunIds: []	已确认没有直接活动运行；null 表示不能枚举精确运行集合
attention: []	已确认没有可见待处理输入；null 表示该信号不可得或尚未完成同步
childIds	只包含获准展示的子会话；null 表示关系未知，不得据此推断没有子任务
progress: null	当前没有可展示的进度卡；具体原因结合能力状态和详情文案解释
时间	均为毫秒时间戳；排序首先使用协议序列与本地 revision，不以客户端时钟猜测事件先后

OpenClaw 对 activeRunIds 的全量与增量语义有明确区分：完整快照缺失该字段时不能沿用旧集合；增量缺失意味着不变，null 表示清除，数组表示替换。适配器必须先正确处理上游差异，再输出本项目的完整 FloorAgent。

4.4 全量、增量与节流

更新环节	语义
首次打开	收到完整快照后建立场景；未建立快照前显示“正在连接”，不显示伪造专员
SSE 建连	服务端先注册观察者并缓冲更新，再发送快照及其后的增量，避免快照读取与监听之间丢事件
完整快照	替换当前展示范围的业务数据；稳定 ID 对应的小人复用，不因刷新重新入场
增量	upserts 中每项是完整实体替换；removeIds 是明确移除；可选顶层字段缺失表示不变
版本检查	增量的 epoch 和 baseRevision 必须匹配本地状态；不匹配时停止应用增量并重新获取快照
新 epoch	代表适配器重建了状态基线；丢弃旧增量，不继续拼接
合并节流	普通实体更新最多每 100 毫秒提交一次；文本摘要最多每 500 毫秒更新一次
重要状态	等待输入、错误、终态和失联通知不得被持续文本流无限推迟；适配器接收后 100 毫秒内提交
渲染	Pixi Ticker 只推进图形动画，不发起状态请求；React 不按 token 更新整棵场景树
临时效果	信封默认 3 秒失效，按事件 ID 去重；初始快照和图形重建不得重播历史效果

场景不得修改传入对象。浏览器侧归并器位于场景库外；替换 OpenClaw 适配器不应要求修改角色或地图代码。

⸻

五、数据源适配器

5.1 已核实的数据面与接入结论

数据面	核实结论	本项目接入
会话列表	Gateway 提供 sessions.list；与智能体工具 sessions_list 不是同一接口名称	直接使用 Gateway RPC
会话状态	会话行及历史快照可提供直接运行状态、运行 ID、模型和用量；并非所有字段在所有版本均存在	基于固定版本 schema 和真实响应逐字段启用
会话订阅	已确认存在 sessions.subscribe 和 sessions.changed	作为会话集合及元数据更新主通道
单会话运行事件	已确认存在 sessions.messages.subscribe；可观察其他客户端发起的运行	对纳入实时观察的会话订阅，而非只订阅用户选中的一个
会话进度小组件	已确认 pluginKind: "session:progress"；其底层存在进度卡 RPC	读取已有 progressCard.get，不抓取控制台 DOM
portal	已确认支持本地 HTTP 服务及流式响应	承载页面和本项目 SSE

会话订阅不是推测性方案；OpenClaw 官方明确描述了列表订阅、逐会话消息订阅及外部客户端旁观运行的行为。
进度卡小组件和底层请求同样有独立文档与 schema。

结论：默认采用“Gateway 订阅 + 周期性快照校准”，轮询是兼容降级，不是主方案。

5.2 客户端、认证与能力检查

适配器使用官方发布的 @openclaw/gateway-client 和 @openclaw/gateway-protocol，不从 OpenClaw 根包内部路径导入私有模块。官方客户端文档给出了 2026.8.1 包、协议 v4 和 Node.js >=22.19.0 的明确基准，同时要求客户端与 Gateway 配套验证；该示例版本不代表目标机器版本，也不能证明所有后续字段均可用。

项目	要求
默认身份	operator，默认仅申请 operator.read
凭据	使用受支持的设备配对和令牌流程；禁止读取控制台浏览器存储冒用身份
方法能力	结合握手宣告、固定版本 schema 和最小只读请求核验；不得只按版本字符串猜测
工具事件	实现后声明 tool-events；未声明时可能没有工具流，不能将其解释为“没有工具在运行”
审批信息	可选；需要经批准的相应权限，不为显示字形申请 operator.admin
可写方法	服务端调用白名单排除消息发送、会话修改、审批处理、进度写入和刷新
无法配对	显示“需要授权”，停止高频重试，不尝试降级绕过认证

tool-events 是实际的事件投递开关，而不是授权替代物。

5.3 字段映射表

OpenClaw 来源	FloorState 目标	映射规则
会话 key、已解析所有者 agentId、Gateway 实例配置	agents[id].session、id	保留原始会话地址；不能只按 agentId 聚合
sessionId	session.sessionId	用于实例隔离和拒绝迟到事件
本地显示别名；否则 label、autoLabel	name	最后回落为可辨识的会话短标识；改名不改变身份
kind	kind	原值透传；不把所有 direct 会话视为主会话
updatedAt	metadataUpdatedAtMs	元数据更新时间，不用作运行判断
lastActivityAt、lastInteractionAt	对应时间字段	分别保留，不混成“正在运行”
hasActiveRun	work.hasActiveRun	直接活动运行的主要依据
activeRunIds	work.activeRunIds	精确集合整体替换；缺失与空数组必须区分
status、lastRunId、lastRunError	work.status、latestOutcome	结合当前活动集合、实例和终态关联判定，不能让旧失败覆盖新运行
model、modelProvider	model.selected*	配置或选择的模型
activeModel、activeModelProvider	model.active*	当前实际运行模型；缺失时不伪造为已观测值
inputTokens、outputTokens、totalTokens、totalTokensFresh、contextTokens	usage	保留原统计口径和新鲜度；不自行计算费用或把 token 转为进度
parentSessionKey、parentSessionId、childSessions	relation	仅关联已确认身份且获准展示的会话
可见子会话活动状态	runningVisibleChildren	只统计可见子会话；不是父会话直接运行状态
agent 生命周期事件	work.status、phase、latestOutcome	按 runId 关联，按该 run 的 seq 排序
工具流 start/update/end	work.tool、可验证的 phase	工具名称和调用关联字段须按目标运行时实测载荷解析
明确的阻塞问题或审批待处理状态	work.attention、waiting_input	必须确认仍待处理且确实阻塞；异步问题不自动改成等待
session.operation，operation: "compact"，phase: "start"/"end"	work.compacting	按会话和 operation 标识配对；断线后未重新确认时置未知
progressCard.get 返回的 card	progress	revision、updatedAt、markdown、steps[].step/status 对应归一化
session.narration.text	work.summary	可选；作为可见工作摘要，不作为任务成功或阻塞依据
列表可见消息投影或按需预览	lastMessagePreview	正文默认关闭；启用后仅保留脱敏短文本
具有确定发送者、接收者和事件标识的会话通信	handoffs	【待验证】；无法确定时不生成信封

会话行中的状态枚举、父子关系、终态运行标识、模型和用量字段以 sessions-row.ts 为依据；直接活动字段另见 Gateway 会话行类型及客户端恢复约定。

消息预览存在 includeLastMessage 请求选项，但目标版本的响应投影字段及裁剪规则仍须固定，不得预先编造 lastMessagePreview 是 Gateway 原生字段；它只是本项目字段。

5.4 订阅初始化与一致性

阶段	规定
会话范围	默认展示用户明确选定的专员会话及获准可见的子会话；外观/展示绑定不是 MD roster，不负责创建或维护会话
列表初始化	先安装事件监听，再以非空列表参数调用 sessions.subscribe；首批使用 limit: 100，正文预览默认关闭
分页	有后续页时按返回的 nextOffset 继续；不得用本地显示条数计算偏移
补齐快照	初始化期间缓冲相关事件；按身份、采样时间和运行序列合并，必要时执行一次尾随校准
逐会话订阅	对实时观察集合内的会话调用 sessions.messages.subscribe，保留其确认的所有者和订阅标识
连接恢复	重新建立订阅并获取新基线；不假设断线期间的事件能够完整重放
不认识的 run	暂不映射到任何小人；触发会话校准，禁止“分给第一个运行中的专员”
事件缺口	检测到 run 序列缺口时，停止依赖缺失的局部状态，读取权威快照恢复
删除和失去可见性	明确权限撤销立即清除；普通列表缺席需排除分页、过滤和部分失败，不直接视为删除

sessions.subscribe 使用空参数时只有订阅确认；非空参数可同时取得初始列表。分页和订阅数据必须遵循 Gateway 的实际返回规则。

读取快照按 snapshotAt 处理新旧，同时间以请求顺序打破平局；该时间不能取代事件顺序或会话身份检查。

agent 事件按每个 runId 独立维护最高 seq，忽略重复与倒序，发现向前缺口后校准。重连时可使用 chat.history.sessionInfo 和 inFlightRun 恢复正在执行的运行，即使它尚无文本。历史读取仅限恢复确有需要的会话，不批量加载全部聊天内容。

5.5 实时摘要与进度卡

实时摘要。 MVP 使用默认单会话订阅模式，只提取状态及已验证的工具元数据。v1 可启用 mode: "narration"：其 session.narration 是可见助手文本的限长快照，通常最多每两秒一次，终态允许立即刷新。该模式属于后续添加的协议 v4 行为，没有独立能力协商保证，因此必须在固定 Gateway 版本上验证后启用；不支持时回到默认订阅，不构造新的事件名。

进度卡。 只调用 progressCard.get。不得调用 progressCard.put，也不得调用 progressCard.refresh；后者可能触发状态更新运行，不符合只读观察边界。

进度卡保存的是持久计划，不保证属于当前活动 run，且其 schema 不包含可直接用于该关联的 runId。因此：

* 仅显示“计划步骤完成数／总数”和最后更新时间，不把它标成可靠的整体任务百分比。
* 卡片存在不代表专员正在运行；步骤全完成不单独触发成功字形。
* 父会话与子会话不得共用一个伪造进度对象；子会话没有卡片时显示未提供。

进度卡的实际字段和步骤状态由协议定义；工具文档明确区分持久卡片与当前运行，并限制其在子智能体中的使用。

对原始 global 等目标，必须保留原始会话 key 与所有者组合。发送显式 agentId 前检查 progress-card-agent-scope-v1；缺失时不得猜测归属。progressCard.changed 如仅提供不能唯一反解原始会话的展示 key，应将其视为候选对象失效通知，分别按原始地址重新读取。

5.6 轮询间隔、配额与降级

情况	本项目约定	界面行为
订阅正常	事件驱动；每 30 秒完成一次会话快照校准	标识“实时”
有事件但缺少可合并字段	250 毫秒合并失效通知；持续通知时最迟 1 秒发起校准	不为每个 token 发起请求
Gateway 可连接，但不支持会话订阅	有运行、排队或待处理输入时每 2 秒轮询；全部静止时每 5 秒	明示“轮询，间隔 2 秒／5 秒”
所有浏览器页面隐藏	轮询降为每 15 秒；可解除逐会话高频内容订阅	恢复可见时立即重新订阅并校准
进度卡支持变化事件	变化后按需读取；已展示卡片每 30 秒校准	无卡片不表示零进度
进度卡无变化事件	仅为已展开的进度面板每 5 秒读取	明示其更新时间
单次 RPC	5 秒超时；同类列表扫描单飞；详情并发最多 4	超时不清空整个办公室
全局读取配额	最多 10 次 RPC／秒；相同目标请求合并	达到配额时显示实际同步延迟
Gateway 连接断开	1、2、4、8、16、30 秒退避，附加 ±20% 抖动	立即标记数据过期；不得把全部专员改为空闲
认证或配对失败	停止自动高频重试，等待有效授权或配置变更	显示“需要授权”
浏览器 SSE 中断	立即重连；45 秒无传输心跳视为失联	保留最后状态并标记过期
portal 无法稳定转发 SSE	浏览器改为每 2 秒读取本项目快照接口	这是浏览器传输降级，不改变服务端 Gateway 接入模式

Gateway 的 WebSocket 本身不可达时，不能声称“改用 sessions.list 轮询就恢复了”。这些 RPC 仍需要可用的 Gateway 连接。

超过 60 秒未得到可接受的权威校准且缺乏有效实时覆盖时，相关实体标记为 stale。正常空闲不能因为没有新消息而变成 stale；判定依据是同步质量，而不是业务活动时间。

扫描未完成、某页失败或达到配额时，不发布具有删除语义的“完整清单”。普通缺席至少需要两次成功完整扫描，并在可用时以精确会话读取确认；权限撤销不适用该宽限。

5.7 多会话与子会话

情况	呈现规则
同一 agent 同时打开多个会话	多个小人；显示专员名及会话短标签；不能共用活动运行集合
同一个会话有多个活动 run	一个小人，显示活动数量；一个 run 结束不得覆盖其余 run 的执行状态
存在非阻塞异步问题	保持运行状态，增加“有待答问题”标记；不得显示为已卡住
父会话空闲、子会话运行	父会话保留自身状态，增加“子会话运行中”标签，不伪造父会话 hasActiveRun=true
子会话关系不完整	独立展示；不通过名字或 key 字符串猜测父节点
会话 key 复用但实例改变	外观可保留，旧实例运行和临时效果必须失效
座位不足	稳定分页或显示候位区域；列表保留所有纳入范围的会话，不叠坐、不静默丢弃
两个浏览器同时打开	后端复用上游观察连接与订阅；浏览器选择、相机、页码相互独立
只有父子关系、没有通信事件	可以显示静态关系，不播放信封

OpenClaw 区分直接运行、子会话运行和精确活动 run 集合；原始 global、unknown 会话还必须与其所有者一起处理，不能与字面上的 agent-qualified key 混淆。

5.8 等待输入的覆盖边界

ask_user 可以真正等待用户，但异步问题允许智能体继续执行，不能把所有问句或所有问题通知归为阻塞。实际问题事件字段、重连后的待处理快照及权限覆盖列入 【待验证 V3】。

审批可通过 sessions.messages.subscribe 的 includeApprovals: true 接收受权限约束的 session.approval，并获得待处理重放；只有重放未截断时才能把它视为完整待处理集合。该接入需要相应审批权限，默认只读模式不能承诺覆盖。

无法获得完整等待信号时，blockingInput 标记为 partial 或 forbidden，界面明确提示覆盖不足；不得用静默时长补出“等待输入”。

⸻

六、状态 → 动画／字形映射

6.1 状态判定优先关系

适配器先判定业务状态，场景再执行视觉映射。

未知与过期优先影响表现；当前执行事实优先于历史终态；仍有可执行 run 时，某个 run 的等待或结束只作为附加信息。

queued 和 stopped 是为避免错误归类而增加的归一化状态。上游会话行确实区分 queued/running/done/failed/interrupted/killed/timeout；不应将这些值强行压缩成“运行／空闲”。

6.2 映射表

可观测状态	判定来源	角色动画	字形	屏幕及中文标签
正在执行	当前直接活动运行；或已关联 run 的开始、工具执行事件	前往座位时 walk；到位后 type	none	屏幕开；“运行中”或工具名
正在读取	已验证的读取类工具事件	到位后 read	none	屏幕开；“读取中”
思考／收尾	明确的粗粒度运行阶段；不读取隐藏推理	read	none	屏幕开；“处理中／收尾中”
等待输入	当前仍待处理、明确阻塞的问题或审批；没有其他可执行 run	idle，停止闲逛	blocked	屏幕停止工作动画；“等待输入／等待审批”
非阻塞待答	异步问题，同时仍在执行	保留当前工作动画	none	增加“有待答问题”标记
运行错误	对应当前实例的运行失败终态，且无其他活动 run	idle	blocked	屏幕关；“运行失败”及短原因
最近一轮成功	成功终态与会话实例、run 关联成立，且活动集合已清空	idle	success，仅触发一次	屏幕关；持续保留“本轮已完成”和完成时间
空闲	权威快照确认无直接活动运行，且没有待处理队列或当前阻塞事实	idle；可选装饰性 walk	none	屏幕关；“空闲”
排队	明确 status: "queued" 或已验证队列状态	idle	none	屏幕关；“排队中”
已取消／中断	明确 interrupted/killed 或取消终态	idle	none	屏幕关；“已停止”，不得庆祝
运行超时	明确运行终态 timeout，不是 RPC 等待超时	idle	blocked	屏幕关；“运行超时”
正在压缩上下文	已关联的 session.operation 压缩开始／结束事件	read	compacting	屏幕开；“整理上下文”
明确循环告警	经验证的上游结构化循环检测信号	未终止时保留工作动作；终止后 idle	looping	“循环告警”；来源未验证时不启用
数据过期／未知	连接失败、序列缺口未恢复、字段缺失	暂停工作动画，保留位置	none	灰化并标明“状态过期／未知”和最后确认时间

工具执行流和生命周期流是运行观测来源；压缩操作的开始、结束有专门的会话事件 schema。

6.3 视觉语义约束

walk 仅表示办公室中的位置变化，不表示 Gateway 的“运行中”。专员走回工位期间仍须通过名牌显示其真实业务状态。

blocked 同时用于等待和错误时，必须通过文字和颜色区分；仅靠同一个感叹号不满足验收。减少动态效果模式下使用静态字形，不以闪烁作为唯一提示。

MD 的 success 字形会在约 0.9 秒后自行消失，因此持续的“本轮已完成”标签必须由业务状态保留，不能依赖瞬时闪光。重复快照、token 更新和 WebGL 重建不得重播完成庆祝。

工具执行失败但智能体继续修复时，不把整个会话标为失败。单独出现 chat.final、进度卡完成、活动时间停止变化或一次查询超时，也不得单独触发完成或错误。

连续长时间无进展最多形成“较久未观察到新进展”的提示，不触发 looping 或 blocked；循环检测事件的具体兼容性见 【待验证 V4】。

⸻

七、角色与美术方案

7.1 专属小人

采用两阶段方案：

阶段	方案	稳定性要求
MVP	复用现有 15 个程序化角色配方，允许用户指定外观	外观绑定保存于本地展示配置；列表重排、改名、重连不换人
v1	复用程序化绘制管线，增加原创专员配方	发型、服装、配色、眼镜等组合形成专员特征；头像与场景小人共享配方

MD 的人物和头像由程序绘制，并非当前仍在使用第三方人物 sheet；现有 15 个配方可以作为视觉起点，但显示名称必须来自专员配置，而不是电视剧人物名。

同一专员有多个会话时，可以使用同一基础配方加稳定配饰或编号，但每个会话必须能独立辨认。超过 15 个会话不构成角色数量上限，也不得随机重排外观。

v1 新配方仍输出兼容的方向和帧结构；若增加真正不同的打字、阅读帧，只修改精灵生成与帧选择，保持 idle/walk/type/read 对外枚举不变。

7.2 地图与图集

MVP 仅启用一个经过校验的办公室主题。座位数量由主题实际可用、可达的座位集合决定，不能从“15 个角色配方”推导出“15 个座位”。

主题安装必须校验：地图尺寸、图集尺寸、GID 范围、碰撞层、出生点、座位唯一性、到座位的可达性以及屏幕覆盖区域。缺失装饰区域允许禁用对应装饰；缺失基础地图或全部有效座位属于主题失败。

7.3 授权合规清单

源码许可与美术许可必须分开处理。署名不能自动解决美术资源再分发权限。

MD 的独立美术许可文件不仅要求署名，还明确限制将资源分发给他人。上游仓库包含购买记录，并不自动证明本项目获得了复制、随包分发或再次公开托管这些资产的权利。

资源	合规要求	发布门槛
MD 抽取源码	保留 MIT 许可证及版权声明，记录本地修改	必须完成
来源于 the-office 的代码	按文件来源保留 ISC 许可链和声明	不得仅用新的项目 MIT 声明覆盖原来源
程序化人物和头像	保留对应源码许可；原创新增配方记录作者	不需要重新引入 LimeZu 人物 sheet
LimeZu 图集	保留单独许可及署名；确认本项目合法使用依据	使用权未确认，不纳入交付
使用该图集的地图	与图集共同审查，不因扩展名是 JSON 就自动视为无美术授权问题	再分发边界未确认，不进入公共包
公开仓库和 npm 包	默认不包含受限制图集及地图资产	使用本机合法授权导入或原创替代
应用署名页	显示 LimeZu、素材名称及要求的作者链接；保留 MD 和上游代码来源	有使用即必须可见
README／项目网站	按实际使用保留对应署名；没有网站时不虚构网站	与应用发布同步检查
字体和其他资源	默认使用系统字体；新增外部资源逐项登记许可	未登记资源不得发布

MD 的资源说明列出了三个实际使用的图集和两份地图，并说明人物 sheet 已被程序化人物替代；其代码来源说明也指向 the-office 的 ISC 项目。

【待验证 V2】 必须对本项目的本机使用、仓库保存和应用分发三种场景分别确认授权；无法确认时保留渲染代码，改用合法取得的资源或原创办公室主题，不将风险转嫁为“保留署名即可”。

⸻

八、里程碑与验收标准

8.1 里程碑

里程碑	交付内容	可检验完成判据
M0：来源与协议基线	固定版本、授权记录、能力矩阵、脱敏事件样本	记录 MD SHA、Gateway 和 SDK 版本；在目标环境完成列表、外部发起运行、成功、失败、等待输入、断线恢复测试；不支持项明确登记
M1：独立场景库	脱离 MD 的办公室场景	只注入测试 FloorState 即可运行；无 @/store/store、window.cth、Electron、PTY、hive 依赖；地图、小人、座位、相机和字形可用
MVP：真实会话办公室	本地服务、Gateway 适配器、portal 页面	至少完成真实会话的运行、等待、失败、完成和空闲展示；订阅和轮询模式均可辨认；同 agent 多会话不混淆；断线不伪造状态
v1：可靠性与个性化	原创配方、子会话、进度卡、容量与恢复优化	全部一致性测试通过；进度卡保持只读；子会话状态不污染父会话；授权、CSP、WebGL 和 portal 验收通过
v1 可选增强	有依据的信封、循环告警、narration	只有对应事件及权限验证通过才启用；未验证能力不阻塞其他已完成部分，但不得宣传为已支持

若目标 Gateway 缺少等待输入等必要信号，只能验收为明确标注能力缺口的降级版，不能把模拟数据验证冒充真实集成验收。

8.2 功能与一致性验收

测试	通过标准
其他客户端发起任务	办公室无需主动发送消息，即能看到对应会话进入运行状态
同一会话并行运行	一个 run 完成而另一个继续时，小人保持工作，活动数量正确
快照与事件竞态	初始化期间制造状态变化，不丢失最终状态，不出现重复小人
乱序和重复	重放重复、倒序事件，不回退状态、不重复庆祝
事件缺口	触发权威校准；恢复前明确标识不确定，不继续渲染伪实时状态
会话实例重建	相同 key 换 sessionId 后，旧 run 的结束事件不能影响新实例
等待与异步问题	阻塞问题显示等待；异步问题仍执行时保持运行并增加待答标记
可恢复工具错误	工具报错后继续运行，不把会话误判成最终失败
取消和查询超时	取消不显示成功；查询超时不改写为运行超时
父子会话	子会话运行不自动令父会话处于直接运行状态
权限撤销	对应会话和预览从服务端投影视图、浏览器和临时效果中清除
分页失败	不因某页未返回删除已有专员
进度卡缺失或过旧	显示未提供或最后更新时间，不输出伪造百分比
信封	每个信封均可追溯真实通信证据；没有证据时数量为零
场景故障	地图失败或 GPU 不可用时仍可通过 DOM 列表查看真实状态

8.3 延迟、容量和资源指标

以下为项目目标，测试机器、浏览器版本、分辨率和地图必须随结果记录。

指标	验收目标
服务端接收事件至可见状态更新	正常本地链路下 P95 不超过 300 毫秒；不包括上游本身尚未发出的事件
轮询发现变化	不超过当时轮询周期加一次成功请求和 500 毫秒呈现预算
MVP 数据容量	20 个纳入观察的会话；本页小人数不超过已校验座位容量
v1 数据容量	100 个会话；稳定分页，不因未进入当前地图页而失去列表状态
前台图形流畅度	基准机器上持续至少 30 FPS；未确定基准前不得声称性能达标
页面隐藏	停止非必要 Pixi 动画；降低数据获取频率
重复挂载	连续挂载／卸载 20 次，不遗留 Canvas、Ticker、事件监听器或额外 Gateway 连接
WebGL 故障	恢复预算耗尽后停止重试并展示列表；不清空 FloorState
只读性	调用审计中无消息发送、会话修改、进度刷新、审批执行或智能体创建
前端泄密检查	构建产物、网络响应、浏览器存储和日志中均无 Gateway 凭据
CSP	严格脚本策略下通过场景初始化、动画、主题回落和恢复测试，不依赖开放 unsafe-eval

⸻

九、风险与未决问题

编号	风险／待验证事项	验证方法	未通过时的处理
V1	【待验证】目标 Gateway、SDK 与公开文档的版本差异	固定实际版本；核对协议 schema；执行方法存在性、字段、事件和重连契约测试；保存脱敏样本	仅启用验证通过的能力；不能按“协议 v4”推断所有增量功能均存在
V2	【待验证】LimeZu 资源的本项目使用及分发授权	核对完整许可和本项目取得资源的依据；对再分发歧义取得明确授权答复	不分发相关图集／地图；使用合法本机资源或原创替代
V3	【待验证】阻塞问题的事件字段、权限和重连恢复	在目标运行时制造阻塞问题、异步问题、审批、超时和取消；检查事件关联及待处理快照	blockingInput 标为部分支持或不可用；不以消息文本、问号或静默时间推断
V4	【待验证】循环检测的可订阅结构化信号	查固定版本协议和事件生产者；在受控测试中触发循环保护，确认 run、原因、清除和终止语义	禁用 looping；只显示已确认的运行或失败状态
V5	【待验证】不同运行时的工具事件载荷	分别录制实际使用模型／运行时的工具 start、update、end；验证名称、调用 ID、会话关联	保留通用“运行中”；不显示推测工具名和阅读动作
V6	【待验证】消息预览及 narration 的实际版本兼容性	核验固定版响应字段；测试空文本撤回、替换、脱敏和权限变更	关闭正文摘要；保留状态和元数据
V7	【待验证】会话间通信事件的发送者和接收者关联	执行受控会话间通信，确认公开可观察事件含可验证的双方身份及去重依据	不播放信封；不得用父子关系或同时活跃替代
V8	【待验证】portal 权限、嵌入、SSE 与来源限制	在实际控制台打开应用；测试鉴权、跨来源嵌入、流式响应、重连和未授权访问	SSE 可退为本项目 HTTP 快照轮询；访问控制不通过则只允许本机使用
V9	【待验证】锁定 Pixi 版本的 CSP 兼容实现	检查该版本兼容模块，执行生产构建严格 CSP 测试	保留经过验证的兼容层；不得放宽安全策略掩盖问题
V10	【待验证】地图座位容量与浏览器性能基线	对选定地图做座位及寻路校验；在目标浏览器和硬件上测量	限制每页小人数、分页或减少装饰，不丢弃会话数据
V11	Gateway 重连期间状态不可完全重建	断线覆盖运行开始、成功、失败、压缩和问题等待等阶段	用新快照建立基线；无法恢复的瞬态字段置未知，不补播事件
V12	长期任务与单轮运行结束语义不同	以多轮任务、父会话让出执行、进度卡保留等场景测试	固定使用“本轮已完成”“父会话空闲，子会话运行中”等准确文案
V13	上游渲染代码继续依赖 MD 新增行为	每次升级检查导入图、全局对象、定时器和业务条件；对比 vendor 修改记录	拒绝带入不属于渲染层的新增模块
V14	原始事件包含超出办公室需要的敏感内容	检查适配器输出白名单、日志和浏览器响应；测试隐私会话与权限撤销	仅保留状态元数据；禁止持久化原始事件正文

最终发布条件

正式运行模式必须满足以下边界：没有观测依据的状态不出现；缺失能力可见；上游凭据不进入浏览器；场景故障不抹掉会话状态；观察页面不改变智能体行为。

未完成验证的增强能力保持关闭，并在能力矩阵中保留对应状态；不得用演示动画、时间阈值或 MD 原有编排事件填补真实数据缺口。
