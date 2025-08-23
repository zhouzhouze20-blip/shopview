import { useQuery } from "@tanstack/react-query";

export default function SimpleFloorPlan() {
  const { data: floorPlan, isLoading, error } = useQuery<{id: string, imageUrl: string}>({
    queryKey: ["/api/floor-plans/active"],
    queryFn: async () => {
      const response = await fetch('/api/floor-plans/active');
      if (!response.ok) throw new Error('Failed to fetch floor plan');
      return response.json();
    }
  });

  if (isLoading) return <div>加载中...</div>;
  if (error) return <div>错误: {(error as Error).message}</div>;

  return (
    <div className="w-full h-screen bg-gray-100 p-4">
      <h1 className="text-2xl font-bold mb-4">楼层平面图测试</h1>
      
      {floorPlan ? (
        <div>
          <p className="mb-4">图片路径: {floorPlan.imageUrl}</p>
          <div className="w-full h-96 border border-gray-300 bg-white">
            <img 
              src={floorPlan.imageUrl} 
              alt="楼层平面图"
              className="w-full h-full object-contain"
              onLoad={() => console.log('图片加载成功')}
              onError={(e) => console.log('图片加载失败:', e)}
            />
          </div>
        </div>
      ) : (
        <div>没有找到平面图数据</div>
      )}
    </div>
  );
}