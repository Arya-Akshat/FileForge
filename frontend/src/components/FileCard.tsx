import { File, Download, Eye, Trash2, Image, Video, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface FileCardProps {
  fileName: string;
  size: string;
  status: "uploaded" | "processing" | "ready" | "failed";
  createdAt: string;
  fileType: "image" | "video" | "document";
  onView: () => void;
  onDownload: () => void;
  onDelete: () => void;
}

const getFileIcon = (type: string) => {
  switch (type) {
    case "image":
      return Image;
    case "video":
      return Video;
    default:
      return FileText;
  }
};

const getStatusVariant = (status: string) => {
  switch (status) {
    case "ready":
      return "default";
    case "processing":
      return "secondary";
    case "failed":
      return "destructive";
    default:
      return "outline";
  }
};

export const FileCard = ({
  fileName,
  size,
  status,
  createdAt,
  fileType,
  onView,
  onDownload,
  onDelete,
}: FileCardProps) => {
  const FileIcon = getFileIcon(fileType);

  return (
    <Card className="hover:shadow-hover transition-all">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4 flex-1 min-w-0">
            <div className="w-12 h-12 bg-accent rounded-lg flex items-center justify-center flex-shrink-0">
              <FileIcon className="w-6 h-6 text-accent-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-foreground truncate">{fileName}</h3>
              <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                <span>{size}</span>
                <span>•</span>
                <span>{createdAt}</span>
              </div>
              <div className="mt-2">
                <Badge variant={getStatusVariant(status)} className="capitalize">
                  {status}
                </Badge>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button size="sm" variant="ghost" onClick={onView}>
              <Eye className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={onDownload}
              disabled={status !== "ready"}
            >
              <Download className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="ghost" onClick={onDelete}>
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
