# 客户记忆目录

每个客户一个文件夹，积累品牌DNA、设计偏好、项目历史。
跟随 git 版本管理，换电脑不丢失。

## 结构
```
clients/
├── {客户名}/
│   ├── brand_grammar.yaml    ← Step 03 F01 生成，每个项目迭代更新
│   ├── preferences.yaml      ← 客户设计偏好（喜欢/讨厌什么）
│   └── project_history.yaml  ← 做过的项目、结果、反馈
```

## 使用
- Step 00：检查 `clients/{客户名}/` 是否存在，存在则加载
- Step 03：加载 brand_grammar.yaml（跳过重新生成，只验证是否过期）
- Step 05：加载 preferences.yaml（调整激进/保守比例）
- Step 07：加载偏好（渲染风格倾向）
- 项目结束：更新 project_history.yaml

## 防覆盖规则

- **project_history.yaml**：只追加，不覆盖。每个项目追加一条记录。
- **brand_grammar.yaml**：版本化追加。新版本块追加在文件头部，保留所有历史版本。每个版本块标注版本号+日期+项目ID+更新原因。系统读取时取最新版本。
- **preferences.yaml**：同brand_grammar规则。
- **禁止**：删除任何历史版本块。如果某条旧语法被证明错误，在新版本中修正并标注"修正V1中的xxx判断"，但保留V1原文。
