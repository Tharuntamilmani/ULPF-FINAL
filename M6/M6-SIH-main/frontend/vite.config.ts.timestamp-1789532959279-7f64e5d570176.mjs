// vite.config.ts
import { defineConfig } from "file:///E:/ULPF/M6/M6-SIH-main/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///E:/ULPF/M6/M6-SIH-main/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
var handleProxyError = (proxy) => {
  proxy.on("error", (_err, _req, res) => {
    if (res && typeof res.writeHead === "function" && !res.headersSent) {
      res.writeHead(503, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        status: "UNAVAILABLE",
        error: "Backend microservices are currently offline. Running in Demo Simulation mode.",
        code: "ECONNREFUSED"
      }));
    }
  });
};
var vite_config_default = defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:18086",
        changeOrigin: true,
        configure: handleProxyError
      },
      "/health": {
        target: "http://127.0.0.1:18086",
        changeOrigin: true,
        configure: handleProxyError
      },
      "/metrics": {
        target: "http://127.0.0.1:18086",
        changeOrigin: true,
        configure: handleProxyError
      },
      "/system-health": {
        target: "http://127.0.0.1:18090",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/system-health/, "/health"),
        configure: handleProxyError
      },
      "/events-api": {
        target: "http://127.0.0.1:18085",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/events-api/, "/v1"),
        headers: {
          Authorization: "Bearer admin-key-secret"
        },
        configure: handleProxyError
      },
      "/gateway-api": {
        target: "http://127.0.0.1:18080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/gateway-api/, "/v1"),
        headers: {
          Authorization: "Bearer key-tenant-cisco-prod"
        },
        configure: handleProxyError
      },
      "/m2-api": {
        target: "http://127.0.0.1:18082",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/m2-api/, "/v1"),
        headers: {
          Authorization: "Bearer system-admin-token"
        },
        configure: handleProxyError
      }
    }
  },
  build: { outDir: "dist", sourcemap: true }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJFOlxcXFxVTFBGXFxcXE02XFxcXE02LVNJSC1tYWluXFxcXGZyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJFOlxcXFxVTFBGXFxcXE02XFxcXE02LVNJSC1tYWluXFxcXGZyb250ZW5kXFxcXHZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9FOi9VTFBGL002L002LVNJSC1tYWluL2Zyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcbmltcG9ydCByZWFjdCBmcm9tICdAdml0ZWpzL3BsdWdpbi1yZWFjdCdcblxuLy8gU3VwcHJlc3MgcHJveHkgRUNPTk5SRUZVU0VEIHRlcm1pbmFsIG5vaXNlIHdoZW4gYmFja2VuZCBtaWNyb3NlcnZpY2VzIGFyZSBvZmZsaW5lXG5jb25zdCBoYW5kbGVQcm94eUVycm9yID0gKHByb3h5OiBhbnkpID0+IHtcbiAgcHJveHkub24oJ2Vycm9yJywgKF9lcnI6IGFueSwgX3JlcTogYW55LCByZXM6IGFueSkgPT4ge1xuICAgIGlmIChyZXMgJiYgdHlwZW9mIHJlcy53cml0ZUhlYWQgPT09ICdmdW5jdGlvbicgJiYgIXJlcy5oZWFkZXJzU2VudCkge1xuICAgICAgcmVzLndyaXRlSGVhZCg1MDMsIHsgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9KVxuICAgICAgcmVzLmVuZChKU09OLnN0cmluZ2lmeSh7XG4gICAgICAgIHN0YXR1czogJ1VOQVZBSUxBQkxFJyxcbiAgICAgICAgZXJyb3I6ICdCYWNrZW5kIG1pY3Jvc2VydmljZXMgYXJlIGN1cnJlbnRseSBvZmZsaW5lLiBSdW5uaW5nIGluIERlbW8gU2ltdWxhdGlvbiBtb2RlLicsXG4gICAgICAgIGNvZGU6ICdFQ09OTlJFRlVTRUQnLFxuICAgICAgfSkpXG4gICAgfVxuICB9KVxufVxuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbcmVhY3QoKV0sXG4gIHNlcnZlcjoge1xuICAgIHBvcnQ6IDUxNzMsXG4gICAgaG9zdDogdHJ1ZSxcbiAgICBwcm94eToge1xuICAgICAgJy9hcGknOiB7XG4gICAgICAgIHRhcmdldDogJ2h0dHA6Ly8xMjcuMC4wLjE6MTgwODYnLFxuICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXG4gICAgICAgIGNvbmZpZ3VyZTogaGFuZGxlUHJveHlFcnJvcixcbiAgICAgIH0sXG4gICAgICAnL2hlYWx0aCc6IHtcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMToxODA4NicsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgICAgY29uZmlndXJlOiBoYW5kbGVQcm94eUVycm9yLFxuICAgICAgfSxcbiAgICAgICcvbWV0cmljcyc6IHtcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMToxODA4NicsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgICAgY29uZmlndXJlOiBoYW5kbGVQcm94eUVycm9yLFxuICAgICAgfSxcbiAgICAgICcvc3lzdGVtLWhlYWx0aCc6IHtcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMToxODA5MCcsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgICAgcmV3cml0ZTogKHBhdGgpID0+IHBhdGgucmVwbGFjZSgvXlxcL3N5c3RlbS1oZWFsdGgvLCAnL2hlYWx0aCcpLFxuICAgICAgICBjb25maWd1cmU6IGhhbmRsZVByb3h5RXJyb3IsXG4gICAgICB9LFxuICAgICAgJy9ldmVudHMtYXBpJzoge1xuICAgICAgICB0YXJnZXQ6ICdodHRwOi8vMTI3LjAuMC4xOjE4MDg1JyxcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxuICAgICAgICByZXdyaXRlOiAocGF0aCkgPT4gcGF0aC5yZXBsYWNlKC9eXFwvZXZlbnRzLWFwaS8sICcvdjEnKSxcbiAgICAgICAgaGVhZGVyczoge1xuICAgICAgICAgIEF1dGhvcml6YXRpb246ICdCZWFyZXIgYWRtaW4ta2V5LXNlY3JldCcsXG4gICAgICAgIH0sXG4gICAgICAgIGNvbmZpZ3VyZTogaGFuZGxlUHJveHlFcnJvcixcbiAgICAgIH0sXG4gICAgICAnL2dhdGV3YXktYXBpJzoge1xuICAgICAgICB0YXJnZXQ6ICdodHRwOi8vMTI3LjAuMC4xOjE4MDgwJyxcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlLFxuICAgICAgICByZXdyaXRlOiAocGF0aCkgPT4gcGF0aC5yZXBsYWNlKC9eXFwvZ2F0ZXdheS1hcGkvLCAnL3YxJyksXG4gICAgICAgIGhlYWRlcnM6IHtcbiAgICAgICAgICBBdXRob3JpemF0aW9uOiAnQmVhcmVyIGtleS10ZW5hbnQtY2lzY28tcHJvZCcsXG4gICAgICAgIH0sXG4gICAgICAgIGNvbmZpZ3VyZTogaGFuZGxlUHJveHlFcnJvcixcbiAgICAgIH0sXG4gICAgICAnL20yLWFwaSc6IHtcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMToxODA4MicsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgICAgcmV3cml0ZTogKHBhdGgpID0+IHBhdGgucmVwbGFjZSgvXlxcL20yLWFwaS8sICcvdjEnKSxcbiAgICAgICAgaGVhZGVyczoge1xuICAgICAgICAgIEF1dGhvcml6YXRpb246ICdCZWFyZXIgc3lzdGVtLWFkbWluLXRva2VuJyxcbiAgICAgICAgfSxcbiAgICAgICAgY29uZmlndXJlOiBoYW5kbGVQcm94eUVycm9yLFxuICAgICAgfSxcbiAgICB9LFxuICB9LFxuICBidWlsZDogeyBvdXREaXI6ICdkaXN0Jywgc291cmNlbWFwOiB0cnVlIH0sXG59KVxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUF5UixTQUFTLG9CQUFvQjtBQUN0VCxPQUFPLFdBQVc7QUFHbEIsSUFBTSxtQkFBbUIsQ0FBQyxVQUFlO0FBQ3ZDLFFBQU0sR0FBRyxTQUFTLENBQUMsTUFBVyxNQUFXLFFBQWE7QUFDcEQsUUFBSSxPQUFPLE9BQU8sSUFBSSxjQUFjLGNBQWMsQ0FBQyxJQUFJLGFBQWE7QUFDbEUsVUFBSSxVQUFVLEtBQUssRUFBRSxnQkFBZ0IsbUJBQW1CLENBQUM7QUFDekQsVUFBSSxJQUFJLEtBQUssVUFBVTtBQUFBLFFBQ3JCLFFBQVE7QUFBQSxRQUNSLE9BQU87QUFBQSxRQUNQLE1BQU07QUFBQSxNQUNSLENBQUMsQ0FBQztBQUFBLElBQ0o7QUFBQSxFQUNGLENBQUM7QUFDSDtBQUVBLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxNQUFNLENBQUM7QUFBQSxFQUNqQixRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRO0FBQUEsUUFDTixRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsUUFDZCxXQUFXO0FBQUEsTUFDYjtBQUFBLE1BQ0EsV0FBVztBQUFBLFFBQ1QsUUFBUTtBQUFBLFFBQ1IsY0FBYztBQUFBLFFBQ2QsV0FBVztBQUFBLE1BQ2I7QUFBQSxNQUNBLFlBQVk7QUFBQSxRQUNWLFFBQVE7QUFBQSxRQUNSLGNBQWM7QUFBQSxRQUNkLFdBQVc7QUFBQSxNQUNiO0FBQUEsTUFDQSxrQkFBa0I7QUFBQSxRQUNoQixRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsUUFDZCxTQUFTLENBQUMsU0FBUyxLQUFLLFFBQVEsb0JBQW9CLFNBQVM7QUFBQSxRQUM3RCxXQUFXO0FBQUEsTUFDYjtBQUFBLE1BQ0EsZUFBZTtBQUFBLFFBQ2IsUUFBUTtBQUFBLFFBQ1IsY0FBYztBQUFBLFFBQ2QsU0FBUyxDQUFDLFNBQVMsS0FBSyxRQUFRLGlCQUFpQixLQUFLO0FBQUEsUUFDdEQsU0FBUztBQUFBLFVBQ1AsZUFBZTtBQUFBLFFBQ2pCO0FBQUEsUUFDQSxXQUFXO0FBQUEsTUFDYjtBQUFBLE1BQ0EsZ0JBQWdCO0FBQUEsUUFDZCxRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsUUFDZCxTQUFTLENBQUMsU0FBUyxLQUFLLFFBQVEsa0JBQWtCLEtBQUs7QUFBQSxRQUN2RCxTQUFTO0FBQUEsVUFDUCxlQUFlO0FBQUEsUUFDakI7QUFBQSxRQUNBLFdBQVc7QUFBQSxNQUNiO0FBQUEsTUFDQSxXQUFXO0FBQUEsUUFDVCxRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsUUFDZCxTQUFTLENBQUMsU0FBUyxLQUFLLFFBQVEsYUFBYSxLQUFLO0FBQUEsUUFDbEQsU0FBUztBQUFBLFVBQ1AsZUFBZTtBQUFBLFFBQ2pCO0FBQUEsUUFDQSxXQUFXO0FBQUEsTUFDYjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQUEsRUFDQSxPQUFPLEVBQUUsUUFBUSxRQUFRLFdBQVcsS0FBSztBQUMzQyxDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
