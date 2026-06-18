# 铺位综合视图 - 桌面版

## 功能概述

这是一个基于React + TypeScript + Canvas的桌面版铺位综合视图系统，类似于您提供的移动端界面，但针对桌面端进行了优化。

## 主要功能

### 🏢 楼层平面图管理
- **多楼栋支持**：A栋、B栋、C栋等
- **多楼层显示**：5F到B2的楼层选择
- **实时切换**：动态切换楼栋和楼层

### 🎨 铺位可视化
- **Canvas绘制**：使用HTML5 Canvas绘制2D平面图
- **多边形铺位**：支持任意形状的铺位区域
- **颜色编码**：不同业态使用不同颜色标识
- **悬停效果**：鼠标悬停显示铺位详细信息

### 🔍 筛选和搜索
- **业态筛选**：餐饮、零售、体验、主力店、空铺
- **状态筛选**：已租用、空置、维护中
- **搜索功能**：按铺位名称或租户名称搜索
- **实时过滤**：筛选结果实时更新

### 🎛️ 交互控制
- **缩放功能**：鼠标滚轮或按钮缩放
- **平移功能**：拖拽移动视图
- **点击选择**：点击铺位查看详情
- **重置视图**：一键重置缩放和平移

## 技术实现

### 前端技术栈
```typescript
- React 18 + TypeScript
- Canvas 2D API
- Tailwind CSS
- Lucide React (图标)
- Wouter (路由)
```

### 核心组件

#### 1. FloorPlanDesktop
主组件，包含完整的铺位综合视图功能

#### 2. 数据结构
```typescript
interface Shop {
  id: string;
  name: string;
  type: 'catering' | 'retail' | 'experience' | 'anchor' | 'vacant';
  coordinates: [number, number][];
  status: 'occupied' | 'vacant' | 'maintenance';
  floor: string;
  building: string;
  area: number;
  monthlyRent: number;
  imageUrl?: string;
  tenantName?: string;
}
```

#### 3. Canvas绘制
- 使用Canvas 2D API绘制铺位多边形
- 支持缩放和平移变换
- 实时渲染和交互

## 使用方法

### 1. 访问页面
```
http://localhost:3000/floor-plan
```

### 2. 基本操作
- **选择楼栋**：左侧面板选择楼栋
- **选择楼层**：左侧面板选择楼层
- **筛选业态**：勾选要显示的业态类型
- **搜索铺位**：在搜索框输入铺位名称
- **缩放视图**：使用工具栏的缩放按钮
- **点击铺位**：点击铺位查看详细信息

### 3. 键盘快捷键
- **鼠标滚轮**：缩放视图
- **拖拽**：平移视图
- **点击**：选择铺位

## 自定义配置

### 1. 添加新铺位
在 `client/src/data/sample-shops.ts` 中添加新的铺位数据：

```typescript
{
  id: 'A1F009',
  name: '新铺位',
  type: 'retail',
  coordinates: [[100, 100], [200, 100], [200, 200], [100, 200]],
  status: 'occupied',
  floor: '1F',
  building: 'A栋',
  area: 100,
  monthlyRent: 12000,
  tenantName: '新租户'
}
```

### 2. 修改颜色方案
在 `FloorPlanDesktop` 组件中修改 `getShopColor` 函数：

```typescript
const getShopColor = (type: string, status: string) => {
  const colorMap = {
    catering: '#ff6b6b',    // 餐饮 - 红色
    retail: '#ffa726',      // 零售 - 橙色
    experience: '#bdbdbd',  // 体验 - 灰色
    anchor: '#757575',      // 主力店 - 深灰色
    vacant: '#000000'       // 空铺 - 黑色
  };
  
  return colorMap[type as keyof typeof colorMap] || '#bdbdbd';
};
```

### 3. 添加新业态
在 `shopTypes` 数组中添加新业态：

```typescript
const shopTypes = [
  { id: 'catering', name: '餐饮', color: '#ff6b6b' },
  { id: 'retail', name: '零售', color: '#ffa726' },
  { id: 'experience', name: '体验', color: '#bdbdbd' },
  { id: 'anchor', name: '主力店', color: '#757575' },
  { id: 'vacant', name: '空铺', color: '#000000' },
  { id: 'newType', name: '新业态', color: '#4caf50' } // 新增
];
```

## 扩展功能

### 1. 3D视图
可以集成Three.js实现3D楼层视图：

```typescript
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

const FloorPlan3D = () => {
  return (
    <Canvas>
      <OrbitControls />
      {/* 3D铺位模型 */}
    </Canvas>
  );
};
```

### 2. 数据持久化
集成后端API实现数据持久化：

```typescript
const useShops = () => {
  return useQuery({
    queryKey: ['shops'],
    queryFn: () => fetch('/api/shops').then(res => res.json())
  });
};
```

### 3. 实时更新
使用WebSocket实现实时数据更新：

```typescript
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // 更新铺位数据
  };
}, []);
```

## 性能优化

### 1. Canvas优化
- 使用 `requestAnimationFrame` 优化渲染
- 实现视口裁剪减少绘制量
- 使用离屏Canvas缓存静态内容

### 2. 数据优化
- 实现虚拟滚动处理大量铺位
- 使用 `useMemo` 缓存计算结果
- 实现数据分页加载

### 3. 交互优化
- 防抖处理鼠标事件
- 使用 `useCallback` 优化事件处理函数
- 实现懒加载和按需渲染

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 开发计划

- [ ] 添加铺位编辑功能
- [ ] 实现拖拽调整铺位大小
- [ ] 添加铺位图片上传
- [ ] 实现数据导入导出
- [ ] 添加打印功能
- [ ] 实现移动端适配

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
