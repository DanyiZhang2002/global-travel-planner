import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import qiankun from 'vite-plugin-qiankun'

/**
 * 关键设计（与 qiankun 工程化方案配套）：
 *
 * 1. `vite-plugin-qiankun` 解决两个核心问题：
 *    a) 把 Vite 默认产物的原生 ESM（import/export）包装成 qiankun 沙箱可 eval 的格式
 *       （否则 qiankun import-html-entry 拉到 `<script>` 文本后 new Function 执行
 *        遇到 `import{...}from "./x.js"` 直接 SyntaxError）
 *    b) 自动暴露 bootstrap / mount / unmount 生命周期到 window，
 *       供主应用 qiankun loadMicroApp 调用
 *    插件 name 必须与主应用 registerMicroApps / loadMicroApp 的 name 一致，
 *    这里用 appCode 作为 name（构建时通过 VITE_APP_NAME 注入；缺省退回 package.json 名）
 *
 * 2. `base` 直接配成 CDN 的【完整 URL】（含 https://、含 buildId 子目录、以 / 结尾）
 *    → 产物 index.html 里所有 <script src> / <link href> 都会是 CDN 绝对路径
 *    → 即便被注入到 dibp.devops.xiaohongshu.com 主站 window，资源仍能定位到 CDN
 *    → qiankun 的 import-html-entry 见到绝对 URL 也不会再做相对路径改写，正常加载
 *
 * 3. 通过环境变量 VITE_CDN_BASE 注入，CI/Skill 在构建前根据 buildId 拼好传入：
 *      VITE_CDN_BASE=https://picasso-private-1251524319.cos.ap-shanghai.myqcloud.com/formula-static/dibp/{buildId}/ \
 *      pnpm build
 *
 * 4. 本地 `pnpm dev` 时 VITE_CDN_BASE 缺省 → base 退化为 '/'，独立调试不受影响
 *
 * 5. 输出文件名带 hash → CDN 长缓存友好（Cache-Control: immutable）
 */
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const cdnBase = env.VITE_CDN_BASE
  const base = command === 'build' && cdnBase ? cdnBase : '/'

  // 校验：构建模式下必须显式指定 CDN base（除非主动声明本地构建）
  if (command === 'build' && !cdnBase && env.ALLOW_LOCAL_BUILD !== 'true') {
    throw new Error(
      '[miniapp-react-starter] 生产构建必须通过 VITE_CDN_BASE 注入 CDN 绝对路径基。\n' +
        '示例：VITE_CDN_BASE=https://your-cdn.com/path/{buildId}/ pnpm build\n' +
        '如确认是本地调试构建，请显式传 ALLOW_LOCAL_BUILD=true',
    )
  }

  // qiankun 子应用 name 必须全局唯一，且与主应用注册时一致
  // 优先使用 VITE_APP_NAME（CI/Skill 在构建时根据 appCode 注入），否则退回模板默认
  const appName = env.VITE_APP_NAME || 'xinglv-riji'

  return {
    plugins: [
      react(),
      qiankun(appName, {
        // useDevMode=true：dev server 也走 qiankun 包装，便于本地起子应用联调
        useDevMode: command === 'serve',
      }),
    ],
    base,
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      manifest: true,
      target: 'es2020',
      cssCodeSplit: true,
      rollupOptions: {
        output: {
          entryFileNames: 'assets/[name]-[hash].js',
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash][extname]',
          // 把 react/react-dom 抽成独立 vendor chunk，便于 CDN 长缓存命中
          manualChunks: {
            'react-vendor': ['react', 'react-dom'],
          },
        },
      },
    },
    server: {
      port: 5173,
      strictPort: false,
    },
  }
})
