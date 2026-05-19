import { Button, Form, Input, Modal, Radio, Switch, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { useState } from 'react';
import { submitMix } from '@/services/downloadApi';
import { uploadAssetWithProcessApi } from '@/services/libraryApi';
import type { AssetItem } from '@/services/libraryApi';

interface MixConfigModalProps {
  open: boolean;
  onClose: () => void;
  selectedAssets: AssetItem[];
}

type AspectRatio = '16:9' | '9:16';
type AudioMode = 'text' | 'file';

export default function MixConfigModal({ open, onClose, selectedAssets }: MixConfigModalProps) {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [audioMode, setAudioMode] = useState<AudioMode>('text');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioFileList, setAudioFileList] = useState<UploadFile[]>([]);
  const [useHighlights, setUseHighlights] = useState(true);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // video_ids are internal asset IDs for locally-stored video files
      const videoIds = selectedAssets
        .filter((a) => a.file_type === 'video')
        .map((a) => String(a.id));

      if (videoIds.length === 0) {
        message.warning('所选素材中没有视频，无法混编');
        return;
      }

      let narrationText: string | undefined;
      let audioFileId: string | undefined;

      if (audioMode === 'text') {
        if (!values.narration_text?.trim()) {
          message.warning('请输入配音文案');
          return;
        }
        narrationText = values.narration_text.trim();
      } else {
        if (!audioFile) {
          message.warning('请上传配音文件');
          return;
        }
      }

      setSubmitting(true);

      // Upload audio file if in file mode
      if (audioMode === 'file' && audioFile) {
        try {
          const uploadRes = await uploadAssetWithProcessApi({ file: audioFile, remove_watermark: false });
          audioFileId = String(uploadRes.id);
        } catch (err: unknown) {
          const d = err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;
          message.error(typeof d === 'string' ? d : '配音文件上传失败');
          setSubmitting(false);
          return;
        }
      }

      const res = await submitMix({
        video_ids: videoIds,
        narration_text: narrationText,
        audio_file_id: audioFileId,
        aspect_ratio: values.aspect_ratio,
        use_highlights: useHighlights,
      });

      message.success(res.message || '混编任务已提交，可在任务中心查看进度');
      form.resetFields();
      setAudioFile(null);
      setAudioFileList([]);
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : '混编提交失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setAudioFile(null);
    setAudioFileList([]);
    setAudioMode('text');
    onClose();
  };

  return (
    <Modal
      title="AI 混编配置"
      open={open}
      onCancel={handleCancel}
      width={600}
      footer={[
        <Button key="cancel" onClick={handleCancel} disabled={submitting}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={submitting} onClick={handleSubmit}>
          提交混编
        </Button>,
      ]}
    >
      <div className="space-y-4">
        {/* Selected assets summary */}
        <div>
          <h4 className="text-sm font-medium text-yc-text-primary mb-2">已选素材 ({selectedAssets.length})</h4>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {selectedAssets.map((asset) => (
              <div
                key={asset.id}
                className="flex items-center gap-2 text-sm text-yc-text-secondary bg-yc-bg-secondary rounded px-2 py-1"
              >
                <span className="shrink-0">
                  {asset.file_type === 'video' ? '🎬' : asset.file_type === 'audio' ? '🔊' : '🖼️'}
                </span>
                <span className="truncate">{asset.title}</span>
              </div>
            ))}
          </div>
        </div>

        <Form form={form} layout="vertical" initialValues={{ aspect_ratio: '9:16' }}>
          {/* Audio mode toggle */}
          <div>
            <h4 className="text-sm font-medium text-yc-text-primary mb-2">配音来源</h4>
            <Radio.Group
              value={audioMode}
              onChange={(e) => setAudioMode(e.target.value as AudioMode)}
              optionType="button"
              buttonStyle="solid"
              options={[
                { label: '输入文案 (TTS)', value: 'text' },
                { label: '上传配音文件', value: 'file' },
              ]}
            />
          </div>

          {audioMode === 'text' ? (
            <Form.Item
              name="narration_text"
              label="配音文案"
              rules={[
                { required: true, message: '请输入配音文案' },
                { max: 2000, message: '文案不能超过2000字' },
                { whitespace: true, message: '不能只输入空格' },
              ]}
            >
              <Input.TextArea
                rows={4}
                placeholder="输入文案内容，系统将自动生成 TTS 配音..."
                showCount
                maxLength={2000}
              />
            </Form.Item>
          ) : (
            <div>
              <Upload
                maxCount={1}
                accept="audio/*"
                fileList={audioFileList}
                beforeUpload={(file) => {
                  setAudioFile(file);
                  setAudioFileList([{ uid: '-1', name: file.name, status: 'done' }]);
                  return false;
                }}
                onRemove={() => {
                  setAudioFile(null);
                  setAudioFileList([]);
                }}
              >
                <Button icon={<UploadOutlined />}>选择配音文件</Button>
              </Upload>
              {!audioFile && (
                <p className="text-xs text-yc-text-tertiary mt-1">支持 MP3、WAV 等音频格式</p>
              )}
            </div>
          )}

          {/* Aspect ratio */}
          <Form.Item
            name="aspect_ratio"
            label="画面比例"
            rules={[{ required: true }]}
          >
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              options={[
                { label: '竖屏 9:16', value: '9:16' },
                { label: '横屏 16:9', value: '16:9' },
              ]}
            />
          </Form.Item>

          {/* Highlights toggle */}
          <div className="flex items-center gap-2">
            <Switch checked={useHighlights} onChange={setUseHighlights} />
            <span className="text-sm text-yc-text-secondary">精彩片段优先</span>
          </div>
        </Form>

        <p className="text-xs text-yc-text-tertiary">
          混编为后台任务，提交后可在任务中心查看进度与结果。
        </p>
      </div>
    </Modal>
  );
}
