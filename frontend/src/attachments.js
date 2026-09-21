/**
 * 图片附件行为（上传 / 预览 / 粘贴 / 拖拽）的唯一实现。
 *
 * 聊天输入框与落地页输入框共用本组合式函数：行为逻辑与 `.glass-input`
 * 材质遵循同一原则——同一语义只有一个事实源，避免在多组件复制后漂移
 * （见 ADR-20260921-LandingInputMaterial）。
 */
import { ref, computed } from 'vue'
import { t, uploadImage } from './store.js'
import { log } from './logger.js'

export const MAX_IMAGES = 4
export const MAX_IMAGE_SIZE = 5 * 1024 * 1024
export const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']

export function useImageAttachments() {
  const pendingImages = ref([])  // [{ key, name, url, id, uploading, error }]
  const dragOver = ref(false)

  const uploadingCount = computed(() => pendingImages.value.filter((i) => i.uploading).length)
  const readyIds = computed(() => pendingImages.value.filter((i) => i.id && !i.error).map((i) => i.id))

  async function addImageFiles(fileList) {
    const files = [...fileList]
    for (const file of files) {
      if (pendingImages.value.length >= MAX_IMAGES) { alert(t('imageMax')); break }
      if (!IMAGE_TYPES.includes(file.type)) { alert(t('imageUnsupported')); continue }
      if (file.size > MAX_IMAGE_SIZE) { alert(t('imageTooBig')); continue }
      const item = {
        key: Date.now() + '-' + Math.random().toString(36).slice(2),
        name: file.name,
        url: URL.createObjectURL(file),
        id: null, uploading: true, error: '',
      }
      pendingImages.value.push(item)
      try {
        const d = await uploadImage(file)
        item.id = d.id
      } catch (e) {
        log.error('image upload failed |', e)
        item.error = e.message || t('imageUploadFail')
      } finally {
        item.uploading = false
      }
    }
  }

  function onImageChange(e) {
    if (e.target.files?.length) addImageFiles(e.target.files)
    e.target.value = ''
  }

  function onPaste(e) {
    const items = e.clipboardData?.items || []
    const files = []
    for (const it of items) {
      if (it.kind === 'file' && it.type.startsWith('image/')) {
        const f = it.getAsFile()
        if (f) files.push(f)
      }
    }
    if (files.length) { e.preventDefault(); addImageFiles(files) }
  }

  function onDrop(e) {
    dragOver.value = false
    const files = [...(e.dataTransfer?.files || [])].filter((f) => f.type.startsWith('image/'))
    if (files.length) { e.preventDefault(); addImageFiles(files) }
  }

  function onDragOver(e) {
    if ([...(e.dataTransfer?.types || [])].includes('Files')) {
      e.preventDefault()
      dragOver.value = true
    }
  }

  function removeImage(item) {
    URL.revokeObjectURL(item.url)
    pendingImages.value = pendingImages.value.filter((i) => i !== item)
  }

  function clearImages() {
    for (const i of pendingImages.value) URL.revokeObjectURL(i.url)
    pendingImages.value = []
  }

  return {
    pendingImages, dragOver, uploadingCount, readyIds,
    addImageFiles, onImageChange, onPaste, onDrop, onDragOver, removeImage, clearImages,
  }
}
