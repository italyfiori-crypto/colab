// 云函数入口文件
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV }) // 使用当前云环境

const db = cloud.database()

// 云函数入口函数
exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext()
  const { action } = event

  try {
    switch (action) {
      case 'processAnalysisFile':
        return await processAnalysisFile(event)
      default:
        return {
          success: false,
          error: `不支持的操作: ${action}`
        }
    }
  } catch (error) {
    console.error('云函数执行错误:', error)
    return {
      success: false,
      error: error.message
    }
  }
}

// 处理字幕解析文件
async function processAnalysisFile(event) {
  const { fileId, bookId, chapterId } = event

  if (!fileId || !bookId || !chapterId) {
    throw new Error('缺少必要参数: fileId, bookId, chapterId')
  }

  try {
    // 1. 从云存储下载解析文件
    const downloadResult = await cloud.downloadFile({
      fileID: fileId
    })

    const fileBuffer = downloadResult.fileContent
    const fileContent = fileBuffer.toString('utf-8')

    // 2. 解析JSON内容
    const analysisRecords = []
    const lines = fileContent.split('\n')

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue

      try {
        const analysisData = JSON.parse(line)

        const record = {
          _id: `${chapterId}-${analysisData.subtitle_index}`,
          book_id: bookId,
          chapter_id: chapterId,
          subtitle_index: analysisData.subtitle_index,
          timestamp: analysisData.timestamp,
          english_text: analysisData.english_text || '',
          chinese_text: analysisData.chinese_text || '',
          sentence_structure: analysisData.sentence_structure || '',
          structure_explanation: analysisData.structure_explanation || '',
          key_words: analysisData.key_words || [],
          fixed_phrases: analysisData.fixed_phrases || [],
          colloquial_expression: analysisData.colloquial_expression || [],
          created_at: Date.now(),
          updated_at: Date.now()
        }

        analysisRecords.push(record)
      } catch (parseError) {
        console.warn(`跳过无效JSON行 ${i + 1}:`, parseError.message)
      }
    }

    if (analysisRecords.length === 0) {
      return {
        success: true,
        message: '没有有效的解析记录',
        stats: { processed: 0, added: 0, updated: 0, skipped: 0, failed: 0 }
      }
    }

    // 3. 查询现有记录
    const existingRecords = await db.collection('analysis')
      .where({
        book_id: bookId,
        chapter_id: chapterId
      })
      .get()

    const existingMap = {}
    existingRecords.data.forEach(record => {
      existingMap[record.subtitle_index] = record
    })

    // 4. 分类处理记录
    const recordsToAdd = []
    const recordsToUpdate = []
    let skipped = 0

    for (const record of analysisRecords) {
      const existing = existingMap[record.subtitle_index]

      if (existing) {
        // 检查是否需要更新
        if (needsUpdate(record, existing)) {
          record.updated_at = Date.now()
          recordsToUpdate.push(record)
        } else {
          skipped++
        }
      } else {
        recordsToAdd.push(record)
      }
    }

    // 5. 执行数据库操作
    let added = 0
    let updated = 0
    let failed = 0

    // 批量添加新记录
    if (recordsToAdd.length > 0) {
      try {
        const addResult = await db.collection('analysis').add({
          data: recordsToAdd
        })
        added = addResult.ids ? addResult.ids.length : recordsToAdd.length
      } catch (error) {
        console.error('批量添加记录失败:', error)
        failed += recordsToAdd.length
      }
    }

    // 批量更新记录
    for (const record of recordsToUpdate) {
      try {
        await db.collection('analysis').doc(record._id).update({
          data: record
        })
        updated++
      } catch (error) {
        console.error(`更新记录失败 ${record._id}:`, error)
        failed++
      }
    }

    return {
      success: true,
      message: '字幕解析数据处理完成',
      stats: {
        processed: analysisRecords.length,
        added,
        updated,
        skipped,
        failed
      }
    }

  } catch (error) {
    console.error('处理字幕解析文件失败:', error)
    throw new Error(`处理字幕解析文件失败: ${error.message}`)
  }
}

// 检查记录是否需要更新
function needsUpdate(newRecord, existingRecord) {
  const keyFields = [
    'timestamp', 'english_text', 'chinese_text',
    'sentence_structure', 'structure_explanation',
    'key_words', 'fixed_phrases', 'colloquial_expression'
  ]

  for (const field of keyFields) {
    const newValue = newRecord[field]
    const existingValue = existingRecord[field]

    // 对数组字段进行特殊处理
    if (Array.isArray(newValue) || Array.isArray(existingValue)) {
      if (JSON.stringify(newValue) !== JSON.stringify(existingValue)) {
        return true
      }
    } else {
      if (newValue !== existingValue) {
        return true
      }
    }
  }

  return false
}