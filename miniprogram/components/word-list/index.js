// 可复用的单词列表组件
Component({
  // 组件的属性列表
  properties: {
    // 单词列表数据
    words: {
      type: Array,
      value: []
    },
    // 显示模式: full(完整) | simple(简化) | readonly(只读)
    mode: {
      type: String,
      value: 'full'
    },
    // 单词类型: new | review | overdue
    wordType: {
      type: String,
      value: 'new'
    },
    // 显示模式: both | chinese-mask | english-mask
    displayMode: {
      type: String,
      value: 'both'
    },
    // 是否显示序号
    showNumber: {
      type: Boolean,
      value: true
    },
    // 自定义样式类
    customClass: {
      type: String,
      value: ''
    }
  },

  // 组件的初始数据
  data: {
    
  },

  // 组件的方法列表
  methods: {
    // 单词点击事件
    onWordTap(e) {
      const { word, index } = e.currentTarget.dataset;
      this.triggerEvent('wordtap', { word, index });
    },

    // 遮罩切换事件
    onToggleMask(e) {
      const { index } = e.currentTarget.dataset;
      // 添加刮刮乐动画效果
      const words = [...this.properties.words];
      words[index].scratching = true;
      
      // 通知父组件更新数据
      this.triggerEvent('maskToggle', { index, words });
      
      // 等待动画完成后执行相应逻辑
      setTimeout(() => {
        this.triggerEvent('maskComplete', { index });
      }, 600);
    },

    // 处理逾期单词
    onHandleOverdue(e) {
      const { index, action } = e.currentTarget.dataset;
      this.triggerEvent('overdueHandle', { index, action });
    }
  }
});