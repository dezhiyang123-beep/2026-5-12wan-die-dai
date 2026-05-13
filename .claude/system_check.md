# 新电脑首次启动检查清单

每次在新电脑/新环境启动系统时，按以下清单检查。

## 自动检查（系统执行）

```
1. 是否在正确分支？（claude/review-design-workflow-5WmMY）
2. CLAUDE.md 是否存在且版本号正确？
3. .claude/steps/ 是否有 00-10 共11个文件？
4. .claude/templates/ 是否存在？
5. .claude/knowledge/ 是否存在？
6. .claude/clients/ 是否存在？
7. settings.local.json 是否存在？
8. 素材库根目录是否存在？（按 素材库_manifest.yaml 中的路径依次检查）
9. DNA卡数量统计
10. DNA卡中引用的图片是否都能找到？（缺失清单）
```

## 手动检查（用户确认）

```
1. 素材库图片是否已同步到本机？（OneDrive/网盘/手动拷贝）
2. 如果是新电脑，素材库路径是否和 素材库_manifest.yaml 中的一致？不一致则修改 素材库_manifest.yaml
```

## 检查结果处理

- 全部通过 → 可以开始项目
- 素材库缺失 → 提示同步素材库
- DNA卡引用断链 → 输出缺失图片清单，用户补图或重新生成DNA卡
- steps文件缺失 → 提示 git pull
