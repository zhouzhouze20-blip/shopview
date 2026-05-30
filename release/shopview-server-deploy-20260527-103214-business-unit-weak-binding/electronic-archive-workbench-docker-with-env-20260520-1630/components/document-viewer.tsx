"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Download,
  Maximize2,
  Minimize2,
  FileText,
  Image as ImageIcon,
  File,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface DocumentViewerProps {
  files: {
    id: string
    name: string
    type: "pdf" | "image" | "other"
    url: string
    pages?: number
  }[]
  currentFileIndex?: number
  onFileChange?: (index: number) => void
  onClose?: () => void
  className?: string
}

export function DocumentViewer({
  files,
  currentFileIndex = 0,
  onFileChange,
  onClose,
  className,
}: DocumentViewerProps) {
  const [fileIndex, setFileIndex] = useState(currentFileIndex)
  const [currentPage, setCurrentPage] = useState(1)
  const [zoom, setZoom] = useState(100)
  const [rotation, setRotation] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)

  const currentFile = files[fileIndex]
  const totalPages = currentFile?.pages || 1

  const handleFileChange = (index: number) => {
    setFileIndex(index)
    setCurrentPage(1)
    setZoom(100)
    setRotation(0)
    onFileChange?.(index)
  }

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 200))
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 50))
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360)

  const handlePrevPage = () => setCurrentPage((prev) => Math.max(prev - 1, 1))
  const handleNextPage = () => setCurrentPage((prev) => Math.min(prev + 1, totalPages))

  const getFileIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="h-4 w-4" />
      case "image":
        return <ImageIcon className="h-4 w-4" />
      default:
        return <File className="h-4 w-4" />
    }
  }

  if (!currentFile) {
    return (
      <div className={cn("flex items-center justify-center h-full bg-muted/30", className)}>
        <div className="text-center text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>暂无附件</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col h-full bg-background border rounded-lg overflow-hidden", className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate max-w-[200px]" title={currentFile.name}>
            {currentFile.name}
          </span>
          {totalPages > 1 && (
            <span className="text-xs text-muted-foreground">
              ({currentPage} / {totalPages})
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Page Navigation */}
          {totalPages > 1 && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handleNextPage}
                disabled={currentPage >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <div className="w-px h-4 bg-border mx-1" />
            </>
          )}

          {/* Zoom Controls */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleZoomOut}
            disabled={zoom <= 50}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-xs w-12 text-center">{zoom}%</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleZoomIn}
            disabled={zoom >= 200}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>

          <div className="w-px h-4 bg-border mx-1" />

          {/* Rotate */}
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleRotate}>
            <RotateCw className="h-4 w-4" />
          </Button>

          {/* Fullscreen */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setIsFullscreen(!isFullscreen)}
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>

          {/* Download */}
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Download className="h-4 w-4" />
          </Button>

          {/* Close */}
          {onClose && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File List Sidebar */}
        {files.length > 1 && (
          <div className="w-48 border-r bg-muted/20 flex-shrink-0">
            <div className="p-2 border-b">
              <span className="text-xs font-medium text-muted-foreground">
                附件列表 ({files.length})
              </span>
            </div>
            <ScrollArea className="h-[calc(100%-36px)]">
              <div className="p-2 space-y-1">
                {files.map((file, index) => (
                  <button
                    key={file.id}
                    onClick={() => handleFileChange(index)}
                    className={cn(
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm transition-colors",
                      index === fileIndex
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted text-foreground"
                    )}
                  >
                    {getFileIcon(file.type)}
                    <span className="truncate flex-1">{file.name}</span>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Preview Area */}
        <div className="flex-1 overflow-auto bg-muted/10 p-4">
          <div
            className="flex items-center justify-center min-h-full"
            style={{
              transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
              transformOrigin: "center center",
            }}
          >
            {currentFile.type === "image" ? (
              <img
                src={currentFile.url}
                alt={currentFile.name}
                className="max-w-full h-auto shadow-lg rounded"
              />
            ) : currentFile.type === "pdf" ? (
              <div className="bg-white shadow-lg rounded-lg overflow-hidden">
                {/* PDF Preview Placeholder */}
                <div className="w-[595px] h-[842px] flex items-center justify-center bg-white">
                  <div className="text-center">
                    <FileText className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">PDF 预览</p>
                    <p className="text-xs text-muted-foreground mt-1">{currentFile.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      第 {currentPage} 页 / 共 {totalPages} 页
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white shadow-lg rounded-lg p-8">
                <div className="text-center">
                  <File className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">无法预览此文件类型</p>
                  <p className="text-xs text-muted-foreground mt-1">{currentFile.name}</p>
                  <Button variant="outline" size="sm" className="mt-4">
                    <Download className="h-4 w-4 mr-2" />
                    下载文件
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
