/**
 * Mock API 服务器 - 用于前端展示（无需数据库）
 * 运行方式: node mock-api-server.js
 */

import http from 'http';

const PORT = 8000;

// Mock 数据
const mockData = {
  stores: [
    {
      store_id: 1,
      store_name: "旗舰店",
      store_code: "STORE001",
      address: "北京市朝阳区XX路XX号",
      contact_phone: "010-12345678",
      phone: "010-12345678",
      manager_name: "张经理",
      contact_email: "store1@example.com",
      is_active: true,
      status: "active",
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    },
    {
      store_id: 2,
      store_name: "分店",
      store_code: "STORE002",
      address: "上海市浦东新区XX路XX号",
      contact_phone: "021-87654321",
      phone: "021-87654321",
      manager_name: "李经理",
      contact_email: "store2@example.com",
      is_active: true,
      status: "active",
      created_at: "2024-01-02T00:00:00",
      updated_at: "2024-01-02T00:00:00"
    }
  ],
  floors: [
    {
      floor_id: 1,
      floor_name: "一层",
      floor_number: 1,
      store_id: 1,
      description: "一层商场",
      area: 5000,
      status: "active",
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    },
    {
      floor_id: 2,
      floor_name: "二层",
      floor_number: 2,
      store_id: 1,
      description: "二层商场",
      area: 4800,
      status: "active",
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    }
  ],
  counters: [
    {
      counter_id: 1,
      counter_code: "C001",
      counter_name: "1号柜位",
      floor_id: 1,
      store_id: 1,
      area: 50,
      status: "occupied",
      position_x: 100,
      position_y: 100,
      width: 50,
      height: 50,
      shape_type: "rectangle",
      monthly_rent: 10000,
      deposit: 50000,
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    },
    {
      counter_id: 2,
      counter_code: "C002",
      counter_name: "2号柜位",
      floor_id: 1,
      store_id: 1,
      area: 45,
      status: "vacant",
      position_x: 200,
      position_y: 100,
      width: 45,
      height: 45,
      shape_type: "rectangle",
      monthly_rent: 9000,
      deposit: 45000,
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    },
    {
      counter_id: 3,
      counter_code: "C003",
      counter_name: "3号柜位",
      floor_id: 1,
      store_id: 1,
      area: 60,
      status: "occupied",
      position_x: 300,
      position_y: 100,
      width: 60,
      height: 60,
      shape_type: "rectangle",
      monthly_rent: 12000,
      deposit: 60000,
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    }
  ],
  tenants: [
    {
      tenant_id: 1,
      tenant_name: "品牌A",
      contact_person: "王总",
      contact_phone: "13800138000",
      email: "branda@example.com",
      status: "active",
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    },
    {
      tenant_id: 2,
      tenant_name: "品牌B",
      contact_person: "赵总",
      contact_phone: "13900139000",
      email: "brandb@example.com",
      status: "active",
      created_at: "2024-01-01T00:00:00",
      updated_at: "2024-01-01T00:00:00"
    }
  ],
  revenue_data: [
    {
      revenue_id: 1,
      counter_id: 1,
      store_id: 1,
      floor_id: 1,
      revenue_date: "2024-01-15",
      daily_revenue: 5000,
      monthly_revenue: 150000,
      year: 2024,
      month: 1,
      day: 15,
      created_at: "2024-01-15T00:00:00"
    },
    {
      revenue_id: 2,
      counter_id: 3,
      store_id: 1,
      floor_id: 1,
      revenue_date: "2024-01-15",
      daily_revenue: 8000,
      monthly_revenue: 240000,
      year: 2024,
      month: 1,
      day: 15,
      created_at: "2024-01-15T00:00:00"
    }
  ]
};

// 路由处理
// 路由处理函数签名: (req, method, query, pathname?, matchedRoute?)
const routes = {
  '/api/stores': (req, method, query) => {
    if (method === 'GET') {
      return { data: mockData.stores };
    }
    return { error: 'Method not allowed' };
  },
  '/api/floors': (req, method, query, pathname) => {
    if (method === 'GET') {
      let floors = [...mockData.floors];
      if (query.storeId) {
        floors = floors.filter(f => f.store_id === parseInt(query.storeId));
      }
      // 返回数组格式（不是 { data: [...] }）
      return floors;
    }
    return { error: 'Method not allowed' };
  },
  '/api/counters': (req, method, query, pathname) => {
    if (method === 'GET') {
      let counters = [...mockData.counters];
      if (query.storeId) {
        counters = counters.filter(c => c.store_id === parseInt(query.storeId));
      }
      if (query.floorId) {
        counters = counters.filter(c => c.floor_id === parseInt(query.floorId));
      }
      return { data: counters };
    }
    return { error: 'Method not allowed' };
  },
  '/api/tenants': (req, method, query, pathname) => {
    if (method === 'GET') {
      return { data: mockData.tenants };
    }
    return { error: 'Method not allowed' };
  },
  '/api/revenue-data': (req, method, query, pathname) => {
    if (method === 'GET') {
      let revenue = [...mockData.revenue_data];
      if (query.storeId) {
        revenue = revenue.filter(r => r.store_id === parseInt(query.storeId));
      }
      if (query.counterId) {
        revenue = revenue.filter(r => r.counter_id === parseInt(query.counterId));
      }
      return { data: revenue };
    }
    return { error: 'Method not allowed' };
  },
  '/api/dashboard/summary': (req, method, query, pathname) => {
    if (method === 'GET') {
      const totalRevenue = mockData.revenue_data.reduce((sum, r) => sum + r.daily_revenue, 0);
      const totalCounters = mockData.counters.length;
      const occupiedCounters = mockData.counters.filter(c => c.status === 'occupied').length;
      return {
        data: {
          total_revenue: totalRevenue,
          total_counters: totalCounters,
          occupied_counters: occupiedCounters,
          vacant_counters: totalCounters - occupiedCounters,
          occupancy_rate: (occupiedCounters / totalCounters * 100).toFixed(2)
        }
      };
    }
    return { error: 'Method not allowed' };
  },
  '/api/revenue-dashboard/summary': (req, method, query, pathname) => {
    if (method === 'GET') {
      const totalDaily = mockData.revenue_data.reduce((sum, r) => sum + (r.daily_revenue || 0), 0);
      const totalMonthly = mockData.revenue_data.reduce((sum, r) => sum + (r.monthly_revenue || 0), 0);
      const topCounters = mockData.counters.map(c => {
        const revenue = mockData.revenue_data.find(r => r.counter_id === c.counter_id);
        return {
          counter_id: c.counter_id,
          counter_code: c.counter_code,
          counter_name: c.counter_name,
          daily_revenue: revenue?.daily_revenue || 0,
          monthly_revenue: revenue?.monthly_revenue || 0,
          floor_name: mockData.floors.find(f => f.floor_id === c.floor_id)?.floor_name || ''
        };
      }).sort((a, b) => (b.monthly_revenue || 0) - (a.monthly_revenue || 0)).slice(0, 5);
      
      const revenueByFloor = mockData.floors.map(floor => {
        const floorCounters = mockData.counters.filter(c => c.floor_id === floor.floor_id);
        const floorRevenue = floorCounters.reduce((sum, c) => {
          const revenue = mockData.revenue_data.find(r => r.counter_id === c.counter_id);
          return sum + (revenue?.monthly_revenue || 0);
        }, 0);
        return {
          floor_id: floor.floor_id,
          floor_name: floor.floor_name,
          daily_revenue: floorRevenue / 30,
          monthly_revenue: floorRevenue
        };
      });
      
      return {
        data: {
          total_daily_revenue: totalDaily,
          total_monthly_revenue: totalMonthly,
          total_yearly_revenue: totalMonthly * 12,
          average_daily_revenue: totalDaily / mockData.counters.length,
          top_performing_counters: topCounters,
          revenue_by_floor: revenueByFloor,
          revenue_trend: 'stable'
        }
      };
    }
    return { error: 'Method not allowed' };
  },
  '/api/revenue-dashboard/counters': (req, method, query, pathname) => {
    if (method === 'GET') {
      let counters = mockData.counters.map(c => {
        const revenue = mockData.revenue_data.find(r => r.counter_id === c.counter_id);
        const floor = mockData.floors.find(f => f.floor_id === c.floor_id);
        const store = mockData.stores.find(s => s.store_id === c.store_id);
        return {
          ...c,
          daily_revenue: revenue?.daily_revenue || 0,
          monthly_revenue: revenue?.monthly_revenue || 0,
          floor_name: floor?.floor_name || '',
          floor_description: floor?.description || '',
          store_name: store?.store_name || '',
          store_id: c.store_id || store?.store_id
        };
      });
      
      if (query.store_id) {
        counters = counters.filter(c => c.store_id === parseInt(query.store_id));
      }
      if (query.floor_id) {
        counters = counters.filter(c => c.floor_id === parseInt(query.floor_id));
      }
      
      // 返回数组格式（不是 { data: [...] }）
      return counters;
    }
    return { error: 'Method not allowed' };
  },
  '/api/revenue-dashboard/counter': (req, method, query, pathname, matchedRoute) => {
    // 处理 /api/revenue-dashboard/counter/:id 格式的路由
    if (method === 'GET') {
      // 从完整路径中提取 counter ID
      const pathParts = pathname.split('/');
      const counterIdStr = pathParts[pathParts.length - 1].split('?')[0]; // 移除查询参数
      const counterId = parseInt(counterIdStr);
      
      if (counterId && !isNaN(counterId)) {
        const counter = mockData.counters.find(c => c.counter_id === parseInt(counterId));
        if (counter) {
          const revenue = mockData.revenue_data.find(r => r.counter_id === counter.counter_id);
          const floor = mockData.floors.find(f => f.floor_id === counter.floor_id);
          const store = mockData.stores.find(s => s.store_id === counter.store_id);
          
          const monthlyRevenue = revenue?.monthly_revenue || 0;
          const dailyRevenue = revenue?.daily_revenue || 0;
          
          return {
            data: {
              counter_id: counter.counter_id,
              counter_code: counter.counter_code,
              counter_name: counter.counter_name,
              floor_name: floor?.floor_name || '',
              store_name: store?.store_name || '',
              area: counter.area,
              daily_revenue: dailyRevenue,
              monthly_revenue: monthlyRevenue,
              yearly_revenue: monthlyRevenue * 12,
              revenue_per_sqm: counter.area > 0 ? monthlyRevenue / counter.area : 0,
              total_sales_profit: monthlyRevenue * 0.3,
              total_fees: monthlyRevenue * 0.1
            }
          };
        }
      }
      return { error: 'Counter not found' };
    }
    return { error: 'Method not allowed' };
  },
  '/api/health': (req, method, query, pathname) => {
    return { status: 'ok', message: 'Mock API Server is running' };
  }
};

// 创建服务器
const server = http.createServer((req, res) => {
  // 设置 CORS 头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  // 处理 OPTIONS 请求
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // ES 模块方式解析 URL
  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;
  const method = req.method;
  const query = Object.fromEntries(parsedUrl.searchParams);

  console.log(`${method} ${pathname}`);

  // 查找路由（支持动态路径和尾部斜杠）
  let handler = null;
  let matchedRoute = null;
  
  // 规范化路径（移除尾部斜杠，除非是根路径）
  const normalizedPath = pathname.replace(/\/+$/, '') || '/';
  
  // 先尝试精确匹配
  if (routes[normalizedPath]) {
    handler = routes[normalizedPath];
    matchedRoute = normalizedPath;
  } else if (routes[pathname]) {
    handler = routes[pathname];
    matchedRoute = pathname;
  } else {
    // 尝试前缀匹配（用于动态路由如 /api/revenue-dashboard/counter/:id）
    for (const route in routes) {
      const routePath = route.replace(/\/+$/, '');
      if (normalizedPath.startsWith(routePath + '/') || normalizedPath === routePath) {
        handler = routes[route];
        matchedRoute = route;
        break;
      }
    }
  }

  if (handler) {
    try {
      // 对于动态路由，传递完整的 pathname 以便提取参数
      const result = handler(req, method, query, pathname, matchedRoute);
      res.writeHead(200);
      res.end(JSON.stringify(result));
    } catch (error) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: error.message }));
    }
  } else {
    // 404 处理
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not Found', path: pathname }));
  }
});

// 启动服务器
server.listen(PORT, '0.0.0.0', () => {
  console.log('========================================');
  console.log('🚀 Mock API 服务器已启动');
  console.log('========================================');
  console.log(`📡 服务器地址: http://localhost:${PORT}`);
  console.log(`📖 API 文档: http://localhost:${PORT}/api/health`);
  console.log('');
  console.log('✅ 支持的 API 端点:');
  console.log('   GET /api/stores - 获取门店列表');
  console.log('   GET /api/floors - 获取楼层列表');
  console.log('   GET /api/counters - 获取柜位列表');
  console.log('   GET /api/tenants - 获取租户列表');
  console.log('   GET /api/revenue-data - 获取收益数据');
  console.log('   GET /api/dashboard/summary - 获取仪表板摘要');
  console.log('   GET /api/health - 健康检查');
  console.log('');
  console.log('💡 提示: 这是 Mock 服务器，返回的是模拟数据');
  console.log('💡 按 Ctrl+C 停止服务器');
  console.log('========================================');
});
