今天主要做了这些事：

填写了 SPEC_blank.docx 里的 Part 3 输入字段 和 Part 4 输出字段。

输入字段包括：student_state、problem_statement、hint_level、constraints
输出字段包括：status、hint、reveals_full_solution、error_message、clarification_question
并且把 spec 的重点对齐到了：

status 必须稳定返回：ok / error / needs_clarification
reveals_full_solution 要单独成字段，方便测试脚本读取
hint_level 只能是 1 / 2 / 3
缺少 student_state 时应返回 error
用户要求“直接给完整代码”这类冲突约束时，应返回 needs_clarification
处理了 SPEC_blank.docx 打不开的问题。

原因是修改 docx 内部 XML 时，Word/WPS 的命名空间前缀被改乱了
后来已修复，并验证文档内容可以被系统工具读取
保留了一份坏文件备份：SPEC_blank.broken_backup.docx
核心理解：

Spec 是 contract，handler 是执行
写 handler 前，先明确输入、输出、错误边界和可测试标准
Success Criteria 不是“写得好不好”，而是“能不能被测试脚本自动判断”