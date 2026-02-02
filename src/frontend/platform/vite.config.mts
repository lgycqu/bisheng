import react from "@vitejs/plugin-react-swc";
import path from "path";
import { defineConfig } from "vite";
import { createHtmlPlugin } from 'vite-plugin-html';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import svgr from "vite-plugin-svgr";
// import { visualizer } from 'rollup-plugin-visualizer';

/**
 * 开启子路由访问
 * 开启后一般外层网管匹配【custom】时直接透传转到内层网关
 * 内层网关访问 api或者前端静态资源需要去掉【custom】前缀
*/
const app_env = { BASE_URL: '' } // /custom

// Use environment variable to determine the target.
//  const target = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:7860";
// 代理到本地 Docker 后端（bisheng API 服务）
const target = process.env.VITE_PROXY_TARGET || "http://localhost:7860";
// MinIO 文件服务（Docker 映射端口 9100）
const fileServiceTarget = process.env.VITE_FILE_SERVICE_TARGET || "http://localhost:9100";

// 公共代理配置
const commonProxyOptions = {
  changeOrigin: true,
  withCredentials: true,
  secure: false,
  ws: true
};

// 带重写功能的配置生成器
const createProxyConfig = (target, rewrite = true) => ({
  ...commonProxyOptions,
  target,
  ...(rewrite && {
    rewrite: (path) => path.replace(new RegExp(`^${app_env.BASE_URL}`), '')
  }),
  configure: (proxy, options) => {
    proxy.on('proxyReq', (proxyReq, req, res) => {
      console.log('Proxying request to:', proxyReq.path);
    });
  }
});

// API路由配置
const apiRoutes = ["/api/", "/health"];
const apiProxyConfig = createProxyConfig(target);
// 文件服务路由配置
const fileServiceRoutes = ["/bisheng", "/tmp-dir"];
const fileServiceProxyConfig = createProxyConfig(fileServiceTarget);
// Client 应用路由（/workspace/ 代理到 Docker 前端）
const clientTarget = process.env.VITE_CLIENT_TARGET || "http://localhost:3001";
const clientRoutes = ["/workspace"];
const clientProxyConfig = createProxyConfig(clientTarget, false);

const proxyTargets = {};

// 添加API路由代理
apiRoutes.forEach(route => {
  proxyTargets[`${app_env.BASE_URL}${route}`] = apiProxyConfig;
});
// 添加文件服务路由代理
fileServiceRoutes.forEach(route => {
  proxyTargets[`${app_env.BASE_URL}${route}`] = fileServiceProxyConfig;
});
// 添加 Client 应用路由代理（/workspace/ -> Docker 前端）
clientRoutes.forEach(route => {
  proxyTargets[`${app_env.BASE_URL}${route}`] = clientProxyConfig;
});


export default defineConfig(() => {
  return {
    base: app_env.BASE_URL || '/',
    build: {
      // minify: 'esbuild', // 使用 esbuild 进行 Tree Shaking 和压缩
      outDir: "build",
      rollupOptions: {
        output: {
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('react-ace') || id.includes('ace-builds') || id.includes('react-syntax-highlighter') || id.includes('rehype-mathjax') || id.includes('react-markdown')) {
                return 'acebuilds';
              }
              if (id.includes('@xyflow/react')) {
                return 'reactflow';
              }
              if (id.includes('pdfjs-dist')) {
                return 'pdfjs';
              }
              if (id.includes('react-window') || id.includes('react-beautiful-dnd') || id.includes('react-dropzone')) {
                return 'reactdrop';
              }

              return
            }
          }
        }
      }
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    plugins: [
      react(),
      svgr(),
      createHtmlPlugin({
        minify: true,
        inject: {
          data: {
            // include: [/index\.html$/],
            aceScriptSrc: `<script src="${process.env.NODE_ENV === 'production' ? app_env.BASE_URL : ''}/node_modules/ace-builds/src-min-noconflict/ace.js" type="text/javascript"></script>`,
            baseUrl: app_env.BASE_URL
          }
        }
      }),
      viteStaticCopy({
        targets: [
          {
            src: [
              'node_modules/ace-builds/src-min-noconflict/ace.js',
              'node_modules/ace-builds/src-min-noconflict/mode-json.js',
              'node_modules/ace-builds/src-min-noconflict/worker-json.js',
              'node_modules/ace-builds/src-min-noconflict/mode-yaml.js',
              'node_modules/ace-builds/src-min-noconflict/worker-yaml.js'
            ],
            dest: 'node_modules/ace-builds/src-min-noconflict/'
          },
          {
            src: 'node_modules/pdfjs-dist/build/pdf.worker.min.js',
            dest: './'
          }
        ]
      }),
      // 打包物体积报告
      // visualizer({
      //   open: true,
      // })
    ],
    define: {
      __APP_ENV__: JSON.stringify(app_env)
    },
    server: {
      host: '0.0.0.0',
      port: 3002,  // 使用 3002 端口，避免与 Docker 前端 3001 冲突
      proxy: {
        ...proxyTargets,
      },
    },
  };
});
