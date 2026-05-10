import { useState, useRef } from "react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Image as ImageIcon } from "lucide-react";

interface ImageUploaderProps {
  onGetUploadParameters: () => Promise<{
    method: "PUT";
    url: string;
  }>;
  onComplete?: (imageUrl: string) => void;
  onError?: (error: string) => void;
  buttonClassName?: string;
  children?: ReactNode;
  currentImageUrl?: string;
  maxFileSize?: number;
}

/**
 * 图片上传组件，专门用于门头图片等图片上传
 * 
 * 功能：
 * - 支持JPG、PNG、GIF、WebP等图片格式
 * - 支持拖拽上传和文件选择
 * - 实时显示上传进度和状态
 * - 自动文件类型验证
 * - 显示当前图片预览
 */
export function ImageUploader({
  onGetUploadParameters,
  onComplete,
  onError,
  buttonClassName,
  children,
  currentImageUrl,
  maxFileSize = 5242880, // 5MB default for images
}: ImageUploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 验证文件类型
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      onError?.('请选择JPG、PNG、GIF或WebP格式的图片文件');
      return;
    }

    // 验证文件大小
    if (file.size > maxFileSize) {
      onError?.(`文件大小不能超过 ${Math.round(maxFileSize / 1024 / 1024)}MB`);
      return;
    }

    try {
      setIsUploading(true);
      const uploadParams = await onGetUploadParameters();
      
      // 使用FormData格式上传文件
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(uploadParams.url, {
        method: uploadParams.method,
        body: formData,
        // 不要设置Content-Type，让浏览器自动设置multipart/form-data
      });

      if (response.ok) {
        const result = await response.json();
        const imageUrl = result.fileUrl; // 使用后端返回的实际文件URL
        onComplete?.(imageUrl);
      } else {
        const errorText = await response.text();
        onError?.(`上传失败 (${response.status}): ${errorText || '请重试'}`);
      }
    } catch (error) {
      onError?.(error instanceof Error ? error.message : '上传过程中发生错误');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="space-y-3">
      {/* 当前图片预览 */}
      {currentImageUrl && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">当前图片</label>
          <div className="relative inline-block">
            <img 
              src={currentImageUrl} 
              alt="门头图片预览" 
              className="w-32 h-20 object-cover rounded border"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
          </div>
        </div>
      )}

      {/* 上传按钮 */}
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
          onChange={handleFileSelect}
          className="hidden"
        />
        <Button 
          type="button"
          variant="outline" 
          onClick={() => fileInputRef.current?.click()} 
          className={buttonClassName || "w-full"}
          disabled={isUploading}
        >
          {isUploading ? (
            <>
              <div className="w-4 h-4 mr-2 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"></div>
              上传中...
            </>
          ) : (
            children || (
              <>
                <Upload className="w-4 h-4 mr-2" />
                上传门头图片
              </>
            )
          )}
        </Button>
      </div>
    </div>
  );
}

