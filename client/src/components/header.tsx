import { Upload, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ObjectUploader } from "./ObjectUploader";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import type { UploadResult } from '@uppy/core';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  selectedStoreId?: number;
}

export default function Header({ searchQuery, onSearchChange, selectedStoreId }: HeaderProps) {
  const { toast } = useToast();

  const handleGetUploadParameters = async () => {
    try {
      const response = await apiRequest('POST', '/api/objects/upload');
      const data = await response.json();
      return {
        method: 'PUT' as const,
        url: data.uploadURL,
      };
    } catch (error) {
      console.error('Error getting upload URL:', error);
      throw error;
    }
  };

  const handleUploadComplete = async (result: UploadResult<Record<string, unknown>, Record<string, unknown>>) => {
    if (result.successful && result.successful.length > 0) {
      const uploadedFile = result.successful[0];
      const imageURL = uploadedFile.uploadURL;
      
      try {
        await apiRequest('PUT', '/api/floor-plans/active/image', { imageURL });
        
        toast({
          title: "楼层图纸上传成功",
          description: "平面图已更新，页面将自动刷新",
        });
        
        // Refresh the page to show the new floor plan
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } catch (error) {
        console.error('Error updating floor plan:', error);
        toast({
          title: "更新失败",
          description: "图纸上传成功但更新楼层平面图失败",
          variant: "destructive",
        });
      }
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4" data-testid="header">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <i className="fas fa-building text-white text-sm"></i>
            </div>
            <h1 className="text-xl font-semibold text-slate-900" data-testid="text-app-title">
              百货柜位管理系统
              {selectedStoreId && (
                <span className="text-sm font-normal text-slate-500 ml-2">
                  (门店ID: {selectedStoreId})
                </span>
              )}
            </h1>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Input
              type="text"
              placeholder="搜索厅房..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 w-64"
              data-testid="input-search"
            />
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
          </div>
          <ObjectUploader
            maxNumberOfFiles={1}
            maxFileSize={50 * 1024 * 1024} // 50MB
            allowedFileTypes={['.jpg', '.jpeg', '.png', '.dwg', '.dxf']}
            onGetUploadParameters={handleGetUploadParameters}
            onComplete={handleUploadComplete}
            buttonClassName="bg-primary text-white hover:bg-blue-700"
          >
            <Upload className="mr-2 h-4 w-4" />
            上传楼层图纸
          </ObjectUploader>
        </div>
      </div>
    </header>
  );
}
