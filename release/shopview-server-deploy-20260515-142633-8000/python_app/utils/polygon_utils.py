#!/usr/bin/env python3
"""
多边形柜位工具类
Polygon counter utilities
"""
import json
import math
from typing import List, Tuple, Dict, Any
from decimal import Decimal


class PolygonUtils:
    """多边形柜位工具类"""
    
    @staticmethod
    def create_rectangle_coordinates(x: float, y: float, width: float, height: float) -> List[List[float]]:
        """创建矩形坐标点"""
        return [
            [x, y],
            [x + width, y],
            [x + width, y + height],
            [x, y + height]
        ]
    
    @staticmethod
    def create_polygon_coordinates(points: List[Tuple[float, float]]) -> List[List[float]]:
        """创建多边形坐标点"""
        return [[point[0], point[1]] for point in points]
    
    @staticmethod
    def calculate_center_point(coordinates: List[List[float]]) -> Tuple[float, float]:
        """计算多边形中心点"""
        if not coordinates:
            return (0.0, 0.0)
        
        x_sum = sum(point[0] for point in coordinates)
        y_sum = sum(point[1] for point in coordinates)
        
        center_x = x_sum / len(coordinates)
        center_y = y_sum / len(coordinates)
        
        return (center_x, center_y)
    
    @staticmethod
    def calculate_bounding_box(coordinates: List[List[float]]) -> Dict[str, float]:
        """计算边界框"""
        if not coordinates:
            return {
                'min_x': 0.0, 'min_y': 0.0,
                'max_x': 0.0, 'max_y': 0.0
            }
        
        x_coords = [point[0] for point in coordinates]
        y_coords = [point[1] for point in coordinates]
        
        return {
            'min_x': min(x_coords),
            'min_y': min(y_coords),
            'max_x': max(x_coords),
            'max_y': max(y_coords)
        }
    
    @staticmethod
    def calculate_polygon_area(coordinates: List[List[float]]) -> float:
        """计算多边形面积（使用鞋带公式）"""
        if len(coordinates) < 3:
            return 0.0
        
        area = 0.0
        n = len(coordinates)
        
        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]
        
        return abs(area) / 2.0
    
    @staticmethod
    def is_point_in_polygon(point: Tuple[float, float], coordinates: List[List[float]]) -> bool:
        """判断点是否在多边形内部（射线法）"""
        x, y = point
        n = len(coordinates)
        inside = False
        
        p1x, p1y = coordinates[0]
        for i in range(1, n + 1):
            p2x, p2y = coordinates[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    @staticmethod
    def coordinates_to_json(coordinates: List[List[float]]) -> str:
        """将坐标点转换为JSON字符串"""
        return json.dumps(coordinates)
    
    @staticmethod
    def json_to_coordinates(json_str: str) -> List[List[float]]:
        """将JSON字符串转换为坐标点"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @staticmethod
    def validate_polygon(coordinates: List[List[float]]) -> bool:
        """验证多边形是否有效"""
        if len(coordinates) < 3:
            return False
        
        # 检查是否有重复点
        points = set((point[0], point[1]) for point in coordinates)
        if len(points) != len(coordinates):
            return False
        
        # 检查面积是否大于0
        area = PolygonUtils.calculate_polygon_area(coordinates)
        return area > 0


class CounterShapeManager:
    """柜位形状管理器"""
    
    @staticmethod
    def create_rectangle_counter(x: float, y: float, width: float, height: float) -> Dict[str, Any]:
        """创建矩形柜位"""
        coordinates = PolygonUtils.create_rectangle_coordinates(x, y, width, height)
        center = PolygonUtils.calculate_center_point(coordinates)
        bbox = PolygonUtils.calculate_bounding_box(coordinates)
        area = width * height
        
        return {
            'shape_type': 'rectangle',
            'polygon_coordinates': PolygonUtils.coordinates_to_json(coordinates),
            'center_x': center[0],
            'center_y': center[1],
            'bounding_box_min_x': bbox['min_x'],
            'bounding_box_min_y': bbox['min_y'],
            'bounding_box_max_x': bbox['max_x'],
            'bounding_box_max_y': bbox['max_y'],
            'area': area,
            # 保持向后兼容
            'position_x': x,
            'position_y': y,
            'width': width,
            'height': height
        }
    
    @staticmethod
    def create_polygon_counter(coordinates: List[List[float]]) -> Dict[str, Any]:
        """创建多边形柜位"""
        if not PolygonUtils.validate_polygon(coordinates):
            raise ValueError("无效的多边形坐标")
        
        center = PolygonUtils.calculate_center_point(coordinates)
        bbox = PolygonUtils.calculate_bounding_box(coordinates)
        area = PolygonUtils.calculate_polygon_area(coordinates)
        
        return {
            'shape_type': 'polygon',
            'polygon_coordinates': PolygonUtils.coordinates_to_json(coordinates),
            'center_x': center[0],
            'center_y': center[1],
            'bounding_box_min_x': bbox['min_x'],
            'bounding_box_min_y': bbox['min_y'],
            'bounding_box_max_x': bbox['max_x'],
            'bounding_box_max_y': bbox['max_y'],
            'area': area,
            # 对于多边形，计算近似的矩形参数
            'position_x': bbox['min_x'],
            'position_y': bbox['min_y'],
            'width': bbox['max_x'] - bbox['min_x'],
            'height': bbox['max_y'] - bbox['min_y']
        }
    
    @staticmethod
    def update_counter_shape(counter_data: Dict[str, Any], new_coordinates: List[List[float]]) -> Dict[str, Any]:
        """更新柜位形状"""
        if not PolygonUtils.validate_polygon(new_coordinates):
            raise ValueError("无效的多边形坐标")
        
        center = PolygonUtils.calculate_center_point(new_coordinates)
        bbox = PolygonUtils.calculate_bounding_box(new_coordinates)
        area = PolygonUtils.calculate_polygon_area(new_coordinates)
        
        # 更新形状相关字段
        counter_data.update({
            'shape_type': 'polygon',
            'polygon_coordinates': PolygonUtils.coordinates_to_json(new_coordinates),
            'center_x': center[0],
            'center_y': center[1],
            'bounding_box_min_x': bbox['min_x'],
            'bounding_box_min_y': bbox['min_y'],
            'bounding_box_max_x': bbox['max_x'],
            'bounding_box_max_y': bbox['max_y'],
            'area': area,
            # 更新近似矩形参数
            'position_x': bbox['min_x'],
            'position_y': bbox['min_y'],
            'width': bbox['max_x'] - bbox['min_x'],
            'height': bbox['max_y'] - bbox['min_y']
        })
        
        return counter_data


# 示例用法
if __name__ == "__main__":
    # 创建矩形柜位
    rect_counter = CounterShapeManager.create_rectangle_counter(100, 100, 50, 30)
    print("矩形柜位:", rect_counter)
    
    # 创建多边形柜位
    polygon_coords = [
        [100, 100],
        [150, 100],
        [180, 130],
        [150, 160],
        [100, 160],
        [80, 130]
    ]
    poly_counter = CounterShapeManager.create_polygon_counter(polygon_coords)
    print("多边形柜位:", poly_counter)
    
    # 验证多边形
    is_valid = PolygonUtils.validate_polygon(polygon_coords)
    print(f"多边形有效: {is_valid}")
    
    # 计算面积
    area = PolygonUtils.calculate_polygon_area(polygon_coords)
    print(f"多边形面积: {area}")






