import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Upload as UploadIcon, X, FileUp } from "lucide-react";
import { toast } from "sonner";
import { filesApi } from "@/lib/api";

const Upload = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [processingOptions, setProcessingOptions] = useState({
    convertFormat: false,
    generateThumbnail: false,
    compressImage: false,
    generatePreview: false,
    extractFrame: false,
    compressVideo: false,
    virusScan: false,
    encryptFile: false,
    decryptFile: false,
    aiTagging: false,
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error("Please select a file first");
      return;
    }

    setIsUploading(true);

    try {
      // Map UI options to backend job types
      const pipelineActions: string[] = [];
      
      if (processingOptions.generateThumbnail) pipelineActions.push("thumbnail");
      if (processingOptions.convertFormat) pipelineActions.push("image_convert");
      if (processingOptions.compressImage) pipelineActions.push("image_compress");
      if (processingOptions.generatePreview) pipelineActions.push("video_preview");
      if (processingOptions.extractFrame) pipelineActions.push("video_thumbnail");
      if (processingOptions.compressVideo) pipelineActions.push("video_convert");
      if (processingOptions.virusScan) pipelineActions.push("virus_scan");
      if (processingOptions.encryptFile) pipelineActions.push("encrypt");
      if (processingOptions.decryptFile) pipelineActions.push("decrypt");
      if (processingOptions.aiTagging) pipelineActions.push("ai_tag");

      // Upload file directly to backend
      const response = await filesApi.uploadFile(selectedFile, pipelineActions);

      toast.success("File uploaded successfully!");
      navigate(`/file/${response.file_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
      console.error("Upload error:", error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleOptionChange = (option: keyof typeof processingOptions) => {
    setProcessingOptions((prev) => ({
      ...prev,
      [option]: !prev[option],
    }));
  };

  return (
    <div className="flex-1 bg-background">
      <div className="max-w-4xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Upload File</h1>
          <p className="text-muted-foreground mt-1">
            Upload a file and select processing options
          </p>
        </div>

        <Card className="mb-6">
          <CardContent className="p-6">
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className="border-2 border-dashed border-border rounded-lg p-12 text-center hover:border-primary transition-colors cursor-pointer"
            >
              <input
                type="file"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              {!selectedFile ? (
                <label htmlFor="file-upload" className="cursor-pointer">
                  <UploadIcon className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-foreground font-medium mb-2">
                    Drop your file here or click to browse
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Support for images, videos, and documents
                  </p>
                </label>
              ) : (
                <div className="flex items-center justify-center gap-4">
                  <FileUp className="w-8 h-8 text-primary" />
                  <div className="text-left">
                    <p className="font-medium text-foreground">
                      {selectedFile.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedFile(null)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <h2 className="text-xl font-semibold text-foreground mb-6">
              Processing Options
            </h2>

            <div className="space-y-6">
              <div>
                <h3 className="font-medium text-foreground mb-3">Images</h3>
                <div className="space-y-3">
                  {[
                    { id: "convertFormat", label: "Convert Format (WebP)" },
                    { id: "generateThumbnail", label: "Generate Thumbnails (64x64, 128x128, 256x256)" },
                    { id: "compressImage", label: "Compress Image" },
                  ].map((option) => (
                    <div key={option.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={option.id}
                        checked={processingOptions[option.id as keyof typeof processingOptions]}
                        onCheckedChange={() =>
                          handleOptionChange(option.id as keyof typeof processingOptions)
                        }
                      />
                      <Label htmlFor={option.id} className="text-sm cursor-pointer">
                        {option.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="font-medium text-foreground mb-3">Videos</h3>
                <div className="space-y-3">
                  {[
                    { id: "generatePreview", label: "Generate Preview (10 seconds)" },
                    { id: "extractFrame", label: "Extract Frame Thumbnail" },
                    { id: "compressVideo", label: "Compress Video" },
                  ].map((option) => (
                    <div key={option.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={option.id}
                        checked={processingOptions[option.id as keyof typeof processingOptions]}
                        onCheckedChange={() =>
                          handleOptionChange(option.id as keyof typeof processingOptions)
                        }
                      />
                      <Label htmlFor={option.id} className="text-sm cursor-pointer">
                        {option.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="font-medium text-foreground mb-3">General</h3>
                <div className="space-y-3">
                  {[
                    { id: "virusScan", label: "Virus Scan" },
                    { id: "encryptFile", label: "Encrypt File" },
                    { id: "decryptFile", label: "Decrypt File" },
                    { id: "aiTagging", label: "AI Auto Tagging" },
                  ].map((option) => (
                    <div key={option.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={option.id}
                        checked={processingOptions[option.id as keyof typeof processingOptions]}
                        onCheckedChange={() =>
                          handleOptionChange(option.id as keyof typeof processingOptions)
                        }
                      />
                      <Label htmlFor={option.id} className="text-sm cursor-pointer">
                        {option.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center gap-4 mt-6">
          <Button onClick={handleUpload} size="lg" disabled={!selectedFile || isUploading}>
            {isUploading ? "Uploading..." : "Upload File"}
          </Button>
          <Button variant="outline" size="lg" onClick={() => navigate("/")} disabled={isUploading}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Upload;
