// 会员管理云函数
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database({
  // 指定 false 后可使得 doc.get 在找不到记录时不抛出异常
  throwOnNotFound: false,
})

exports.main = async (event, context) => {
  const { action, ...params } = event
  const wxContext = cloud.getWXContext()
  const userId = wxContext.OPENID

  try {
    switch (action) {
      case 'activateCode':
        return await activateCode(userId, params)
      case 'checkMembership':
        return await checkMembership(userId)
      case 'getMembershipHistory':
        return await getMembershipHistory(userId)
      default:
        return {
          success: false,
          message: '未知的操作类型'
        }
    }
  } catch (error) {
    console.error('会员管理云函数执行错误:', error)
    return {
      success: false,
      message: error.message || '服务器错误'
    }
  }
}

/**
 * 激活会员码
 */
async function activateCode(userId, { code }) {
  console.log('📋 [DEBUG] 激活会员码:', { userId, code })

  if (!code || typeof code !== 'string') {
    return {
      success: false,
      message: '请输入有效的会员码'
    }
  }

  // 去除空格并转大写
  const cleanCode = code.trim().toUpperCase()

  if (cleanCode.length !== 12) {
    return {
      success: false,
      message: '会员码格式错误，应为12位字符'
    }
  }

  try {
    // 查询会员码是否存在且可用
    const codeResult = await db.collection('membership_codes').doc(cleanCode).get()

    if (!codeResult.data) {
      return {
        success: false,
        message: '会员码不存在或已失效'
      }
    }

    const codeData = codeResult.data

    // 检查会员码状态
    if (!codeData.active) {
      return {
        success: false,
        message: '会员码已被禁用'
      }
    }

    if (codeData.use_status === 'used') {
      return {
        success: false,
        message: '会员码已被使用'
      }
    }

    if (codeData.use_status === 'expired') {
      return {
        success: false,
        message: '会员码已过期'
      }
    }

    // 计算会员到期时间
    const codeType = parseInt(codeData.code_type)
    const extendDays = getDaysByCodeType(codeType)

    if (extendDays === 0) {
      return {
        success: false,
        message: '无效的会员码类型'
      }
    }

    const currentTime = Date.now()

    // 获取用户当前会员信息
    let userMembership
    try {
      const membershipResult = await db.collection('user_memberships').doc(userId).get()
      userMembership = membershipResult.data
    } catch (err) {
      // 用户会员记录不存在，创建新的
      userMembership = null
    }

    let newExpireTime
    if (userMembership && userMembership.expire_time && userMembership.expire_time > currentTime) {
      // 用户是活跃会员，在现有时间基础上延长
      newExpireTime = userMembership.expire_time + (extendDays * 24 * 60 * 60 * 1000)
    } else {
      // 用户是新会员或已过期，从现在开始计算
      newExpireTime = currentTime + (extendDays * 24 * 60 * 60 * 1000)
    }

    // 准备激活记录
    const activationRecord = {
      code: cleanCode,
      code_type: codeData.code_type,
      activated_at: currentTime
    }

    // 使用事务确保数据一致性
    try {
      const result = await db.runTransaction(async transaction => {
        // 1. 更新会员码状态
        await transaction.collection('membership_codes').doc(cleanCode).update({
          data: {
            use_status: 'used',
            used_at: currentTime,
            used_by: userId,
            updated_at: currentTime
          }
        })

        // 2. 更新或创建用户会员信息
        if (userMembership) {
          // 更新现有记录
          const updatedActivatedCodes = userMembership.activated_codes || []
          updatedActivatedCodes.push(activationRecord)

          await transaction.collection('user_memberships').doc(userId).update({
            data: {
              expire_time: newExpireTime,
              activated_codes: updatedActivatedCodes,
              updated_at: currentTime
            }
          })
        } else {
          // 创建新记录
          await transaction.collection('user_memberships').add({
            data: {
              _id: userId,
              expire_time: newExpireTime,
              activated_codes: [activationRecord],
              created_at: currentTime,
              updated_at: currentTime
            }
          })
        }

        // 返回事务结果
        return {
          userId,
          code: cleanCode,
          codeType: codeData.code_type,
          extendDays,
          newExpireTime
        }
      })

      console.log('✅ [DEBUG] 会员码激活成功:', result)

      return {
        success: true,
        message: '会员码激活成功！',
        membership_info: {
          type: 'premium',
          expire_time: result.newExpireTime,
          extended_days: result.extendDays,
          code_type: getCodeTypeName(codeType)
        }
      }

    } catch (transactionError) {
      console.error('❌ [DEBUG] 事务执行失败:', transactionError)

      return {
        success: false,
        message: '激活失败，请稍后重试'
      }
    }

  } catch (error) {
    console.error('❌ [DEBUG] 激活会员码失败:', error)
    return {
      success: false,
      message: '激活失败：' + error.message
    }
  }
}

/**
 * 检查会员状态
 */
async function checkMembership(userId) {
  console.log('📋 [DEBUG] 检查会员状态:', userId)

  try {
    const result = await db.collection('user_memberships').doc(userId).get()

    if (!result.data) {
      // 用户没有会员记录，返回免费用户状态
      return {
        success: true,
        data: {
          is_premium: false,
          membership_type: 'free',
          expire_time: null,
          days_remaining: 0,
          status: 'free'
        }
      }
    }

    const membershipData = result.data
    const currentTime = Date.now()

    // 检查是否过期
    const isExpired = membershipData.expire_time && membershipData.expire_time <= currentTime
    const isPremium = membershipData.expire_time && !isExpired

    let daysRemaining = 0
    if (isPremium) {
      daysRemaining = Math.ceil((membershipData.expire_time - currentTime) / (24 * 60 * 60 * 1000))
    }

    console.log('✅ [DEBUG] 会员状态检查结果:', {
      userId,
      isPremium,
      expireTime: membershipData.expire_time ? new Date(membershipData.expire_time) : null,
      daysRemaining,
      isExpired
    })

    return {
      success: true,
      data: {
        is_premium: isPremium,
        membership_type: isPremium ? 'premium' : 'free',
        expire_time: membershipData.expire_time,
        days_remaining: daysRemaining,
        status: isExpired ? 'expired' : (isPremium ? 'active' : 'free')
      }
    }

  } catch (error) {
    console.error('❌ [DEBUG] 检查会员状态失败:', error)
    return {
      success: false,
      message: '检查会员状态失败：' + error.message
    }
  }
}

/**
 * 获取会员激活历史
 */
async function getMembershipHistory(userId) {
  console.log('📋 [DEBUG] 获取会员历史:', userId)

  try {
    const result = await db.collection('user_memberships').doc(userId).get()

    if (!result.data || !result.data.activated_codes) {
      return {
        success: true,
        data: {
          history: [],
          total_count: 0
        }
      }
    }

    const activatedCodes = result.data.activated_codes || []

    // 按激活时间倒序排序
    const sortedHistory = activatedCodes
      .sort((a, b) => b.activated_at - a.activated_at)
      .map(record => ({
        code: maskCode(record.code),
        code_type: record.code_type,
        code_type_name: getCodeTypeName(parseInt(record.code_type)),
        activated_at: record.activated_at,
        activated_date: new Date(record.activated_at).toLocaleDateString('zh-CN')
      }))

    return {
      success: true,
      data: {
        history: sortedHistory,
        total_count: sortedHistory.length
      }
    }

  } catch (error) {
    console.error('❌ [DEBUG] 获取会员历史失败:', error)
    return {
      success: false,
      message: '获取会员历史失败：' + error.message
    }
  }
}

/**
 * 根据会员码类型获取延长天数
 */
function getDaysByCodeType(codeType) {
  const typeMap = {
    1: 365,    // 1年
    2: 730,    // 2年
    5: 1825,   // 5年
    99: 36500  // 终身（100年）
  }
  return typeMap[codeType] || 0
}

/**
 * 获取会员码类型名称
 */
function getCodeTypeName(codeType) {
  const nameMap = {
    1: '1年会员',
    2: '2年会员',
    5: '5年会员',
    99: '终身会员'
  }
  return nameMap[codeType] || '未知类型'
}

/**
 * 隐藏会员码中间部分
 */
function maskCode(code) {
  if (!code || code.length !== 12) {
    return code
  }
  return code.substring(0, 4) + '****' + code.substring(8)
}