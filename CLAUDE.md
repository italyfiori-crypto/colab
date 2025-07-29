# CLAUDE.md

这个文件为Claude Code (claude.ai/code)在此代码仓库中工作提供指导。

## 项目概述

这是一个基于微信云开发平台构建的微信小程序项目，包含云函数。该项目是一个名为"云开发 QuickStart"的英语学习应用，提供多种类别的互动英语课程，如日常对话、商务英语、旅游英语和学术英语。

## 架构说明

### 前端结构 (`miniprogram/`)
- **入口文件**: `app.js` 初始化微信云开发环境配置
- **页面结构**: 多页面应用，带有标签页导航
  - `pages/articles/` - 主要文章列表页，包含搜索和筛选功能
  - `pages/article-detail/` - 单个文章详情页
  - `pages/index/` - 首页
  - `pages/example/` - 示例/演示页
- **组件**: `components/` 目录下的可复用UI组件
- **配置**: `app.json` 定义页面路由和全局设置

### 后端结构 (`cloudfunctions/`)
- **云函数**: 部署到微信云的服务端函数
- **主函数**: `quickstartFunctions/` 通过事件类型切换处理多种操作
  - 数据库操作 (sales集合的增删改查)
  - 用户认证 (获取OpenID)
  - 小程序二维码生成
  - 文件存储操作

### 核心功能
- 文章浏览，支持分类筛选 (全部, 日常对话, 商务英语, 旅游英语, 学术英语)
- 文章标题和描述的搜索功能
- 底部标签页导航系统
- 微信云数据库集成，实现数据持久化
- 云存储文件管理

## 开发命令

### 云函数部署
```bash
# 使用提供的脚本部署云函数
./uploadCloudFunction.sh
# 脚本执行: ${installPath} cloud functions deploy --e ${envId} --n quickstartFunctions --r --project ${projectPath}
```

### 微信开发者工具
- 在微信开发者工具IDE中打开项目
- 使用内置的预览和调试功能
- 通过二维码在微信模拟器或真实设备上测试

## 配置说明

- **环境设置**: 在 `app.js` 的 globalData.env 中配置云环境ID
- **项目配置**: `project.config.json` 包含微信特定的构建设置
- **应用ID**: 项目配置中当前设置为 `wx7040936883aa6dad`
- **云函数根目录**: `cloudfunctions/` 目录
- **小程序根目录**: `miniprogram/` 目录

## 数据结构

### 文章数据模型
```javascript
{
  id: number,
  category: string, // '日常对话' | '商务英语' | '旅游英语' | '学术英语'
  title: string,
  description: string,
  duration: string, // 例如: '5分钟'
  level: string, // '初级' | '中级' | '高级'
  image: string // 图片URL
}
```

### 云数据库集合
- **sales**: 用于演示的示例集合，包含地区/城市/销售数据

## 导航结构
- 底部标签页导航，包含4个标签页：首页、学习记录、收藏、我的
- 只有第一个标签页(文章页)完全实现
- 其他标签页显示"功能开发中"占位符

## 开发指导原则
- 总是使用中文回答
- 尽量使用微信小程序原生组件和框架
- 记住我的名字， 我叫余Sir