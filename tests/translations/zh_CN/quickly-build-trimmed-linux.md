---
status: translated
title: 如何快速构建一个裁剪过的Linux内核
author: Linux Kernel Community
collector: tttturtle-russ
collected_date: 20240718
translator: tttturtle-russ
translated_date: 20240912
link: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/admin-guide/quickly-build-trimmed-linux.rst
---
# 如何快速构建一个裁剪过的 Linux 内核

本指南解释了如何快速构建适用于测试目的的 Linux 内核，这些内核也完全适合日常使用。

## 过程的核心（即“TL;DR”）

*如果你是 Linux 编译的新手，请忽略这个 TLDR 部分，直接前往下一节：下一节提供了一个逐步指南，虽然更详细但仍简洁易懂；该指南及其附带的参考部分还提到了替代方法、常见陷阱和额外注意事项，这些可能对你很重要。*

如果你的系统使用了诸如 Secure Boot 之类的技术，请先配置好系统以允许启动自行编译的 Linux 内核；安装编译器及所有构建 Linux 所需的工具；确保你的主目录中有 12 GB 的可用空间。

现在运行以下命令下载最新的 Linux 主线源码，然后使用这些源码来配置、构建并安装你自己的内核：

```bash
git clone --depth 1 -b master \
  https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git ~/linux/
cd ~/linux/
# 提示：如果你想应用补丁，请在此时操作。详情请参见下方。
# 提示：建议在此时为你的构建打标签。详情请参见下方。
yes "" | make localmodconfig
# 提示：此时你可能想要调整构建配置；如果你使用的是 Debian 系统，则必须这么做。
# 详情请参见下方。
make -j $(nproc --all)
# 注意：在许多常见发行版中，下一条命令就足够了，但在 Arch Linux 及其衍生系统
# 或一些其他系统上则不够。详情请参见下方。
command -v installkernel && sudo make modules_install install
reboot
```

如果你之后想要构建一个更新的主线快照，请使用以下命令：

```bash
cd ~/linux/
git fetch --depth 1 origin
# 注意：下一条命令将丢弃你对代码所做的任何更改：
git checkout --force --detach origin/master
# 提醒：如果你想（重新）应用补丁，请在此时操作。
# 提醒：你可能想要在此时添加或修改一个构建标签。
make olddefconfig
make -j $(nproc --all)
# 提醒：下一条命令在某些发行版上不足以完成安装。
command -v installkernel && sudo make modules_install install
reboot
```

## 逐步指南

从原理上讲，编译你自己的 Linux 内核很容易。有多种方式可以实现。哪种方法最适合你，取决于具体情况。

---
status: translated
title: 从源码快速安装 Linux 内核指南
author: 原文作者
collector: original_collector
collected_date: 20240912
translator: your_github_id
translated_date: 20240912
link: https://example.com/linux-kernel-installation-guide
---

本指南描述了一种非常适合那些希望从源代码快速安装 Linux 而无需被复杂细节困扰的方法；其目标是涵盖主流 Linux 发行版在通用 PC 或服务器硬件上运行时通常所需的一切。

这种安装方法非常适合测试目的，例如尝试一个提出的修复程序，或检查某个问题是否已在最新的代码库中修复。尽管如此，以这种方式构建的内核也完全适合日常使用，同时也很容易保持最新。

以下步骤描述了该过程的重要方面；随后的参考部分将更详细地解释每一个步骤。它有时还会描述替代方法、潜在陷阱以及可能在特定点发生的错误——以及如何在此类情况下重新使系统正常运行。

::: {#backup_sbs}

### 备份

> - 创建一个全新的系统备份，并准备好系统修复和恢复工具，以防万一出现意外情况。

> \[`详细信息<backup>`{.interpreted-text role="ref"}\]

:::

::: {#secureboot_sbs}

### 安全启动（Secure Boot）

> - 在使用“安全启动”或类似技术的平台上，提前做好准备以确保系统允许你自行编译的内核稍后能够启动。在通用 x86 系统上最快速简便的方法是在 BIOS 设置工具中禁用此类技术；或者，可以通过运行 `mokutil --disable-validation` 启动一个流程来解除其限制。

> \[`详细信息<secureboot>`{.interpreted-text role="ref"}\]

:::

::: {#buildrequires_sbs}

### 构建依赖

> - 安装构建 Linux 内核所需的所有软件。通常你需要：'bc'、'binutils'（包括 'ld' 等）、'bison'、'flex'、'gcc'、'git'、'openssl'、'pahole'、'perl'，以及 'libelf' 和 'openssl' 的开发头文件。参考部分展示了如何在各种流行的 Linux 发行版上快速安装这些软件。

> \[`详细信息<buildrequires>`{.interpreted-text role="ref"}\]

:::

::: {#diskspace_sbs}

### 磁盘空间

> - 确保有足够的空闲空间用于构建和安装 Linux。对于安装，/lib/ 分区中预留 150 MB，/boot/ 分区中预留 100 MB 是安全的选择。对于源码和构建产物的存储，在你的家目录中通常 12 GB 的空间就足够了。如果你的可用空间较少，请务必查看参考部分中关于调整内核构建配置的步骤：其中提到了一个技巧，可以将家目录所需的空间减少到大约 4 GB。

> \[`详细信息<diskspace>`{.interpreted-text role="ref"}\]

:::

::: {#sources_sbs}

---
status: translated
title: 获取 Linux 源码并打补丁
author: 原文作者
collector: collecter_github_id
collected_date: 20240912
translator: translator_github_id
translated_date: 20240912
link: https://example.com/original-article-link
---

> - 获取你打算构建的 Linux 版本的源代码；然后进入存放这些源代码的目录，因为本指南中所有后续命令都应从该目录执行。
>
> \[注意：以下段落描述了如何通过部分克隆 Linux 稳定版的 git 仓库来获取源代码。这被称为浅层克隆。参考部分介绍了两个替代方法：`打包的归档文件<sources_archive>`{.interpreted-text role="ref"} 和 `完整的 git 克隆<sources_full>`{.interpreted-text role="ref"}；如果你不介意大批量下载数据，建议使用后者，因为这样可以避免一些 `浅层克隆所具有的特殊特性<sources_shallow>`{.interpreted-text role="ref"}。\]
>
> 首先，执行以下命令以获取一个全新的主线代码库：
>
>     git clone --no-checkout --depth 1 -b master \
>       https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git ~/linux/
>     cd ~/linux/
>
> 如果你想访问最近的主线发行版和预发行版，请将你克隆的历史记录加深到你感兴趣的最旧的主线版本：
>
>     git fetch --shallow-exclude=v6.0 origin
>
> 如果你想访问一个稳定版/长期支持版（例如 v6.1.5），只需添加包含该版本系列的分支；之后至少获取到启动该系列的主线版本（v6.1）的历史记录：
>
>     git remote set-branches --add origin linux-6.1.y
>     git fetch --shallow-exclude=v6.0 origin
>
> 现在检出你感兴趣的代码。如果你刚刚完成了初始克隆，你可以检出一个全新的主线代码库，这对于检查开发者是否已经修复了某个问题是理想的：
>
>     git checkout --detach origin/master
>
> 如果你加深了你的克隆，你可以将 `origin/master` 替换为你加深到的版本（如上面的 `v6.0`）；像 `v6.1` 这样的后续发行版和像 `v6.2-rc1` 这样的预发布版本也适用。如果你按照上述方法添加了相应的稳定版/长期支持版分支，像 `v6.1.5` 这样的稳定版或长期支持版也同样适用。
>
> \[`详情<sources>`{.interpreted-text role="ref"}\]

:::

::: {#patching_sbs}

> - 如果你想应用一个内核补丁，现在就可以进行。通常，像下面这样的命令就能完成任务：
>
>     patch -p1 < ../proposed-fix.patch
>
> 是否需要 `-p1` 参数取决于补丁是如何创建的；如果不成功，可以尝试去掉该参数。
>
> 如果你是用 git 克隆的源代码，并且一切变得混乱，运行 `git reset --hard` 可以撤销对源代码的所有更改。
>
> \[`详情<patching>`{.interpreted-text role="ref"}\]

:::

---
status: translated
title: 自定义内核构建配置
author: ""
collector: yidao620c
collected_date: 20240912
translator: yidao620c
translated_date: 20240912
link: ""
---

如果你打了内核补丁或者已经安装了相同版本的内核，最好为即将构建的内核添加一个独特的标签：

```bash
echo "-proposed_fix" > localversion
```

之后运行 `uname -r` 将会显示类似 `6.1-rc4-proposed_fix` 的信息。

[参见相关标签说明](#tagging)

:::{#configuration_sbs}

- 基于现有配置创建内核的构建配置。

  如果你已经手动准备好了 `.config` 文件，将其复制到 `~/linux/` 目录下并运行：

  ```bash
  make olddefconfig
  ```

  如果你的发行版或他人已经为你的系统或硬件定制了运行中的内核配置，也可以使用相同的命令：`make olddefconfig` 会尝试使用当前运行内核的 `.config` 作为基础。

  对于其他用户来说，使用这个 make 目标也没问题 —— 但你通常可以通过以下命令节省大量时间：

  ```bash
  yes "" | make localmodconfig
  ```

  这条命令会尝试以发行版的内核配置作为基础，然后禁用那些在你的系统中明显多余的模块功能。这将极大缩短编译时间，特别是当你使用的是通用 Linux 发行版提供的通用内核时。

  但需要注意一点：`localmodconfig` 可能会禁用自你上次启动 Linux 以来未使用过的功能 —— 比如当前断开连接的外设驱动，或尚未使用的虚拟化软件支持。你可以通过参考章节中提到的一些技巧来降低或几乎消除这种风险；但对于只是为了快速测试而构建的内核来说，缺少这些功能通常可以忽略不计。不过，当你使用通过此 make 目标构建的内核时，应牢记这一点，因为这可能是你偶尔才使用的一些功能失效的原因。

  [参见配置详情](#configuration)

:::

:::

:::{#configmods_sbs}

---
status: translated
title: 内核配置、构建与安装指南
author: 佚名
collector: WUDAIjun
translator: WUDAIjun
collected_date: 20240912
translated_date: 20240912
link: https://example.com
---

### 配置内核选项

- 检查是否需要调整某些内核配置选项：

  - **调试符号的处理方式**  
    如果你之后可能需要解码例如在 'panic'、'Oops'、'warning' 或 'BUG' 中发现的堆栈跟踪信息，请启用调试符号；另一方面，如果你存储空间有限或希望得到更小的内核二进制文件，请禁用调试符号。有关如何操作的详细信息，请参阅参考章节。如果上述情况都不适用，可能完全可以忽略此项。  
    [详情 \<configmods_debugsymbols\>](#configmods_debugsymbols)

  - **是否在使用 Debian？**  
    如果是，请参考参考章节中提到的额外调整，以避免已知问题。  
    [详情 \<configmods_distros\>](#configmods_distros)

  - **是否需要调整其他配置项？**  
    可以使用像 `menuconfig` 或 `xconfig` 这样的 make 目标进行配置。  
    [详情 \<configmods_individual\>](#configmods_individual)

---

### 构建内核

- 构建内核镜像和模块：

```bash
make -j $(nproc --all)
```

如果你想将内核打包为 `.deb`、`.rpm` 或 `.tar` 文件，请参阅参考章节中的替代方法。  
[详情 \<build\>](#build)

---

### 安装内核

- 安装你的内核：

```bash
command -v installkernel && sudo make modules_install install
```

通常，之后你只需执行一次 `reboot`，因为许多通用 Linux 发行版会自动为你创建 initramfs（也称为 initrd）并在引导加载程序配置中添加新内核条目；但在某些发行版中，你需要手动完成这两个步骤，原因请参阅参考章节。

在一些发行版（如 Arch Linux 及其衍生版本）上，上述命令完全无效；在这种情况下，请按照参考章节中的说明手动安装内核。

如果你使用的是不可变（immutable）Linux 发行版，请查阅其文档和网络资源，了解如何在其中安装自己的内核。  
[详情 \<install\>](#install)

---

::: {#configmods_debugsymbols}

### 调试符号配置说明

启用调试符号有助于分析内核崩溃或警告信息。可以通过以下配置选项控制：

- `CONFIG_DEBUG_INFO=y`：启用调试符号。
- `CONFIG_DEBUG_INFO_NONE=y`：禁用调试符号。

如果你不确定是否需要，可以暂时不启用，等出现问题时再重新编译。

:::

::: {#configmods_distros}

### 针对 Debian 的额外配置

如果你正在使用 Debian 系统，请注意以下事项：

- 使用 `make deb-pkg` 来生成 `.deb` 包，这样更容易管理安装和卸载。
- 确保安装了必要的依赖包，如 `libncurses-dev`、`flex`、`bison`、`libssl-dev` 等。

:::

::: {#configmods_individual}

### 自定义配置方法

使用以下命令进入图形化配置界面：

```bash
make menuconfig   # 基于终端的配置工具
make xconfig      # 基于 GUI 的配置工具（需要 Qt 环境）
make nconfig      # 基于 ncurses 的配置工具
```

你可以在此界面中启用/禁用特定模块或功能。

:::

::: {#build}

### 构建替代方法

除了直接使用 `make`，还可以使用以下命令生成打包好的内核：

```bash
make bindeb-pkg    # 生成 .deb 包（适用于 Debian/Ubuntu）
make rpm-pkg       # 生成 .rpm 包（适用于 Fedora/RHEL）
make targz-pkg     # 生成 tar.gz 归档包
```

这些命令会生成包含内核模块和文档的完整包。

:::

::: {#install}

### 手动安装内核步骤

在不支持自动安装的系统上，你需要手动完成以下步骤：

1. **安装模块**：

```bash
sudo make modules_install dtbs_install
```

2. **安装内核镜像**：

```bash
sudo cp arch/x86_64/boot/bzImage /boot/vmlinuz-$(make kernelrelease)
```

3. **创建 initramfs：**

```bash
sudo dracut --force /boot/initramfs-$(make kernelrelease).img $(make kernelrelease)
```

4. **更新 GRUB：**

```bash
sudo grub-mkconfig -o /boot/grub/grub.cfg
```

5. **重启系统：**

```bash
sudo reboot
```

:::

---
status: translated
title: 后续构建其他内核及卸载说明
author: 原文作者
collector: airwindow
collected_date: 20240912
translator: airwindow
translated_date: 20240912
link: https://example.com
---

> - 要想以后构建另一个内核，你需要执行类似的步骤，但有时命令会略有不同。
>
> 首先，切换回源码目录：
>
>     cd ~/linux/
>
> 如果你想要构建一个你尚未使用过的稳定版/长期支持版本（例如 6.2.y），请告诉 git 要跟踪它：
>
>     git remote set-branches --add origin linux-6.2.y
>
> 现在获取最新的上游更改；你需要再次指定你关心的最早版本，否则 git 可能会检索整个提交历史：
>
>     git fetch --shallow-exclude=v6.0 origin
>
> 接下来切换到你感兴趣的版本 —— 但请注意，这里使用的命令将会丢弃你所做的任何修改，因为它们会与你要检出的源码冲突：
>
>     git checkout --force --detach origin/master
>
> 此时你可以再次对源码打补丁或设置/修改构建标签，如前所述。之后使用 olddefconfig 调整构建配置，以适应新的代码库，这将使用你之前通过 localmodconfig 准备好的配置文件（~/linux/.config）来为下一个内核做好准备：
>
>     # 提示：如果你想应用补丁，请在此时进行
>     # 提示：你可能在此时更新你的构建标签
>     make olddefconfig
>
> 现在构建你的内核：
>
>     make -j $(nproc --all)
>
> 之后按照上述方法安装内核：
>
>     command -v installkernel && sudo make modules_install install
>
> \[`详情<another>`{.interpreted-text role="ref"}\]

:::

::: {#uninstall_sbs}

> - 你的内核日后很容易卸载，因为它的组件仅存储在两个地方，并且可以通过内核的发布名称清晰识别。只需确保不要删除你当前正在运行的内核，因为这可能会导致系统无法启动。
>
> 首先删除存放你的内核模块的目录，该目录以发布名称命名 —— 在以下示例中为 '6.0.1-foobar'：
>
>     sudo rm -rf /lib/modules/6.0.1-foobar
>
> 接下来尝试运行以下命令，该命令在某些发行版上会删除所有其他安装的内核文件，并从引导加载程序配置中移除该内核条目：
>
>     command -v kernel-install && sudo kernel-install -v remove 6.0.1-foobar
>
> 如果该命令没有任何输出或执行失败，请参阅参考章节；如果 /boot/ 中仍存在名为 '\*6.0.1-foobar\*' 的文件，也请执行同样操作。
>
> \[`详情<uninstall>`{.interpreted-text role="ref"}\]

:::

::: {#submit_improvements}

---
status: translated
title: 翻译反馈与文档改进建议
author: Thorsten Leemhuis
collector: openeuler-kunpeng
collected_date: 20240912
translator: openeuler-kunpeng
translated_date: 20240912
link: https://example.com
---

在遵循上述步骤的过程中，你是否遇到了某些问题，而这些问题并未在下面的参考章节中得到解答？或者你是否有改进本文内容的建议？如果是这样的话，请抽出一点时间，通过电子邮件告知本文档的维护者（Thorsten Leemhuis \<linux@leemhuis.info>），如果可以的话，同时抄送给 Linux 文档邮件列表（<linux-doc@vger.kernel.org>）。此类反馈对于进一步改进文档至关重要，这符合所有人的利益，因为它将帮助更多人掌握本文所描述的任务。

## 分步指南的参考章节

本节为上述指南中每一步提供了额外的信息。

### 为紧急情况做好准备 {#backup}

> *创建一份全新的备份，并准备好系统修复和恢复工具* \[`... <backup_sbs>`{.interpreted-text role="ref"}\]

请记住，你在操作的是计算机，它们有时会出现意外行为——尤其是在你修改操作系统核心组件（例如内核）的时候。而这正是你即将进行的操作。因此，即使问题发生的可能性很小，也最好为意外情况做好准备。

\[`返回分步指南 <backup_sbs>`{.interpreted-text role="ref"}\]

### 应对诸如 Secure Boot 的技术 {#secureboot}

> *在支持 "Secure Boot" 或类似技术的平台上，请提前做好准备以确保系统允许稍后引导你自行编译的内核。* \[`... <secureboot_sbs>`{.interpreted-text role="ref"}\]

许多现代系统只允许启动某些特定的操作系统；因此，默认情况下它们会拒绝启动你自己编译的内核。

你可以通过使用证书和签名来使你的平台信任你自己构建的内核。此处不描述具体操作步骤，因为这需要多个步骤，超出了本文的范围；'Documentation/admin-guide/module-signing.rst' 和一些网页已经对此有更详细的说明。

另一种方式是暂时禁用 Secure Boot 等功能以启动你自己的 Linux 系统。在常见的 x86 系统上，你可以在 BIOS 设置工具中完成此操作；具体操作步骤因设备而异，因此此处也不详细描述。

---
status: translated
title: 在主流 x86 Linux 发行版中，还有第三个通用选项
author: 未知（原文未提供作者信息）
collector: collector_github_id
collected_date: 20240912
translator: translator_github_id
translated_date: 20240912
link: https://example.com/original-article-link
---

在主流的 x86 Linux 发行版中，还有第三个通用选项：为你的 Linux 环境禁用所有安全启动（Secure Boot）限制。你可以通过运行 `mokutil --disable-validation` 来启动这个过程；系统会提示你创建一个一次性密码，这个密码可以安全地记录下来。现在重启系统；在 BIOS 完成所有自检后，引导加载程序 Shim 将会显示一个蓝色对话框，提示信息为“Press any key to perform MOK management”（按下任意键执行 MOK 管理）。在倒计时结束前按下任意键。这将打开一个菜单，选择其中的“Change Secure Boot state”（更改安全启动状态）选项。Shim 的“MokManager”现在会要求你输入之前指定的一次性密码中的三个随机字符。一旦你输入了这些字符，请确认你确实想要禁用验证。完成后，允许 MokManager 重启机器。

[返回分步指南 `<secureboot_sbs>`{.interpreted-text role="ref"}]

### 安装构建需求 {#buildrequires}

> *安装构建 Linux 内核所需的所有软件。*  
> \[`...<buildrequires_sbs>`{.interpreted-text role="ref"}\]

Linux 内核本身相对独立，但除了像编译器这样的工具外，你有时还需要一些库来完成构建。如何安装所有必需的组件取决于你的 Linux 发行版以及你即将构建的内核配置。

以下是一些主流发行版上通常需要的内容示例：

> - Debian、Ubuntu 及其衍生版本：
>
>     sudo apt install bc binutils bison dwarves flex gcc git make openssl \
>       pahole perl-base libssl-dev libelf-dev
>
> - Fedora 及其衍生版本：
>
>     sudo dnf install binutils /usr/include/{libelf.h,openssl/pkcs7.h} \
>       /usr/bin/{bc,bison,flex,gcc,git,openssl,make,perl,pahole}
>
> - openSUSE 及其衍生版本：
>
>     sudo zypper install bc binutils bison dwarves flex gcc git make perl-base \
>       openssl openssl-devel libelf-dev

如果你想知道为什么这些列表中包含了 openssl 及其开发头文件：这是因为许多发行版在 x86 机器的内核配置中启用了安全启动支持。

有时你还需要用于压缩格式（如 bzip2、gzip、lz4、lzma、lzo、xz 或 zstd）的工具。

如果你执行的任务不在本指南的覆盖范围内，可能还需要额外的库及其开发头文件。例如，从 tools/ 目录构建内核工具时需要 zlib；使用 `menuconfig` 或 `xconfig` 等 make 目标调整构建配置时，则需要 ncurses 或 Qt5 的开发头文件。

\ [`返回分步指南 <buildrequires_sbs>`{.interpreted-text role="ref"}\]

### 存储空间需求 {#diskspace}

> *确保有足够的可用空间用于构建和安装 Linux。*  
> \ [`... <diskspace_sbs>`{.interpreted-text role="ref"}\]

文中提到的数字是粗略的估计值，并额外增加了冗余以确保安全，因此很多时候你实际需要的空间会更少。

---
status: translated
title: 如果你有空间限制，请记得在进行配置调整时阅读参考部分
author: 原文作者
collector: collecter_github_id
collected_date: 20240912
translator: translator_github_id
translated_date: 20240912
link: https://example.com
---

如果你受到空间限制，请记住在你到达[“关于配置调整的部分”](#configmods)时要阅读参考章节，因为确保关闭调试符号可以节省数 GB 的磁盘空间。

[返回分步指南](#diskspace_sbs)

### 下载源代码 {#sources}

> *获取你打算构建的 Linux 版本的源代码。* [...](#sources_sbs)

分步指南概述了如何使用浅层 git 克隆来获取 Linux 的源代码。这种方法还有[更多内容](#sources_shallow)值得介绍，并且还有两种替代方法值得一提：[打包的归档文件](#sources_archive) 和 [完整 git 克隆](#sources_full)。此外，还有一些方面也需要详细说明，例如“使用一个合适的预发布版本是否比使用最新的主线代码更明智” [详见此处](#sources_snapshot)，以及“如何获取更新鲜的主线代码库” [详见此处](#sources_fresher)。

请注意，为了保持简单，本指南中使用的命令会将构建产物存储在源代码树中。如果你更倾向于将它们分开，只需在所有 make 调用中添加类似 `O=~/linux-builddir/` 的参数；同时也要调整所有添加文件或修改生成文件（例如你的 `.config`）的命令中的路径。

[返回分步指南](#sources_sbs)

#### 浅层克隆的显著特点 {#sources_shallow}

分步指南中使用了浅层克隆，因为对于本文档的大多数目标读者来说，这是最佳解决方案。这种方法有几个方面值得提及：

---
status: translated
title: 使用浅层克隆优化 Git 获取操作
author: 原文作者
collector: orz-z
collected_date: 20240912
translator: orz-z
translated_date: 20240912
link: https://example.com
---

> - 本文档多数地方使用 `git fetch` 命令配合 `--shallow-exclude=` 参数来指定你关心的最早版本（或者更准确地说，是它的 Git 标签）。你也可以使用 `--shallow-since=` 参数，指定一个绝对日期（如 `'2023-07-15'`）或相对时间（如 `'12个月'`）来定义你想下载的历史深度。作为第二种替代方式，除非你添加了用于稳定/长期支持内核的分支，你也可以使用类似 `--depth=1` 的参数显式指定某个深度。
>
> - 在运行 `git fetch` 时，请记得始终指定你关心的最旧版本、时间点或显式深度，如分步指南中所示。否则，你可能会下载几乎完整的 Git 历史记录，这将耗费大量时间和带宽，并对服务器造成压力。
>
>   注意，你并不总是必须使用相同的版本或日期。但当你随时间更改它时，Git 会加深或缩短历史记录到指定的点。这允许你检索最初认为不需要的版本 —— 或者在例如你想释放磁盘空间时，丢弃旧版本的源代码。后者在使用 `--shallow-since=` 或 `--depth=` 时会自动发生。
>
> - 请注意，当你加深克隆时，可能会遇到类似 `'fatal: error in object: unshallow cafecaca0c0dacafecaca0c0dacafecaca0c0da'` 的错误。在这种情况下，请运行 `git repack -d` 然后重试。
>
> - 如果你想从某个特定版本（例如 Linux 6.3）回退更改，或者执行二分查找（v6.2..v6.3），最好告诉 `git fetch` 获取对象到更早的三个版本（比如 6.0）：这样 `git describe` 就能像在完整 Git 克隆中一样描述大多数提交。

[返回分步指南 <sources_sbs>](#)  
[返回章节介绍 <sources>`{.interpreted-text role="ref"}](#)

### 使用包归档文件下载源码 {#sources_archive}

刚接触 Linux 编译的人通常认为，通过 <https://kernel.org> 的首页下载归档文件是获取 Linux 源码的最佳方法。在你确定只构建一个特定内核版本且不修改任何代码的情况下，这确实可能是一个合适的方式。问题是：你可能现在确信自己只会用一个版本，但在实际中，这个假设往往不成立。

这是因为当报告或调试问题时，开发者通常会要求你尝试另一个版本。他们也可能建议你使用 `git revert` 临时撤销某个提交，或者提供多个补丁供你测试。有时报告者也会被要求使用 `git bisect` 来查找导致问题的更改。这些操作都依赖 Git，或者至少在使用 Git 的情况下更容易和快速完成。

---
status: translated
title: 浅层克隆与完整克隆：选择合适的内核源代码获取方式
author: 未知（原文未提供具体作者）
collector: yujunz
collected_date: 20240912
translator: yujunz
translated_date: 20240912
link: https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/
---

浅层克隆也不会带来显著的额外开销。例如，当你使用 `git clone --depth=1` 创建一个最新的主线代码库的浅层克隆时，Git 所获取的数据只比通过 kernel.org 首页下载最新的主线预发布版（即“rc”版本）略多一点。

因此，浅层克隆通常是更优的选择。如果你仍然希望使用打包好的源代码归档文件，请通过 kernel.org 下载一个；然后将其内容解压到某个目录，并进入解压过程中生成的子目录。该逐步指南的其余部分仍然可以正常进行，除了依赖 Git 的部分——这主要影响到关于连续构建其他版本的章节。

[返回逐步指南](sources_sbs) [返回本节介绍](sources)

### 使用完整 Git 克隆下载源代码 {#sources_full}

如果你不介意下载和存储大量数据（截至 2023 年初约为 4.4 GB），你可以选择执行完整的 Git 克隆，而不是使用浅层克隆。这样你就可以避免上述提到的各种特殊情况，并且随时可以访问所有版本和提交记录：

```bash
curl -L \
  https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/clone.bundle \
  -o linux-stable.git.bundle
git clone linux-stable.git.bundle ~/linux/
rm linux-stable.git.bundle
cd ~/linux/
git remote set-url origin \
  https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
git fetch origin
git checkout --detach origin/master
```

[返回逐步指南](sources_sbs) [返回本节介绍](sources)

### 正确的预发布版本（RC）与最新主线版本的区别 {#sources_snapshot}

当你使用 Git 克隆源代码并检出 `origin/master` 时，通常会获得一个介于最新发布版与下一个版本之间的代码库。在尝试使用主线版本时，这几乎总是你所需要的代码：像 v6.1-rc5 这样的预发布版本在发布前并不会经过显著的额外测试。

但有一个例外情况：你可能希望在下一个版本的首个预发布版（如 v6.2-rc1）发布之前，坚持使用最新的主线正式发布版本（比如 v6.1）。这是因为在这段时间内更容易出现编译错误和其他问题，因为此时主线正处于“合并窗口”阶段：通常持续两周，在此期间会合并下个版本的大部分变更。

[返回逐步指南](sources_sbs) [返回本节介绍](sources)

### 避免主线版本滞后 {#sources_fresher}

---
status: translated
title: 内核源码配置与构建指南
author: 某某内核文档贡献者
collector: yingshaoxo
collected_date: 20240912
translator: yingshaoxo
translated_date: 20240912
link: https://example.com/linux-kernel-guide
---

浅层克隆和完整克隆的说明都从 Linux 稳定版 Git 仓库中获取代码。这对本文档的读者来说简化了操作，因为它允许轻松访问主线版本以及稳定版/长期支持版本。这种方法只有一个缺点：

合并到主线仓库中的更改每隔几小时才会同步到 Linux 稳定版仓库的 master 分支。这种延迟大多数情况下无需担心；但如果您确实需要最新的代码，只需将主线仓库作为额外的远程仓库添加，并从那里检出代码：

    git remote add mainline \
      https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
    git fetch mainline
    git checkout --detach mainline/master

在进行浅层克隆时，请记得使用前面描述的参数之一调用 `git fetch` 以限制深度。

\ [`返回分步指南 <sources_sbs>`{.interpreted-text role="ref"}\] \ [`返回章节介绍 <sources>`{.interpreted-text role="ref"}\]

### 修补源代码（可选）{#patching}

> *如果您想应用一个内核补丁，请现在进行。*
> \ [`...<patching_sbs>`{.interpreted-text role="ref"}\]

这是