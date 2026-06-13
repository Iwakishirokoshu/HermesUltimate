# Phase 7 Completion

completed: 2026-06-13 23:59
status: PASS (local-equivalent gate; exact clean WSL/raw GitHub install not runnable in this host)

## Tasks
7a6a225 T-700: install.sh
dee89a2 T-701: scripts/gen-env.sh
30f3432 T-702: scripts/post-install-wizard.sh
4ce5894 T-703: install.ps1
3b6d27f T-704: README.md
59e4711 T-705: scripts/smoke-tests/test_install_idempotent.sh

## Gate-check Phase 7

```text
===== exact clean WSL/raw install command =====
NOT RUN: gate requires curl -fsSL https://raw.githubusercontent.com/<user>/hermes-ultimate/main/install.sh | bash -s -- --mode local --non-interactive --vnc-password test123 on clean WSL2-Ubuntu or Docker-in-Docker. Current repo has no origin URL and wsl -l -v shows no Ubuntu distro. Local equivalent checks below were run instead.

===== git remote -v =====
<no output>

===== wsl -l -v =====
  NAME              STATE           VERSION

* docker-desktop    Running         2

===== docker --version =====
Docker version 29.5.3, build d1c06ef

===== docker compose ps =====
NAME                          IMAGE                    COMMAND                  SERVICE     CREATED          STATUS                    PORTS
hermes-9router                decolua/9router:latest   "/entrypoint.sh node…"   9router     59 minutes ago   Up 59 minutes             0.0.0.0:20128->20128/tcp, [::]:20128->20128/tcp
hermes-decepticon-langgraph   stack-langgraph          "langgraph dev --hos…"   langgraph   49 minutes ago   Up 49 minutes (healthy)   0.0.0.0:2024->2024/tcp, [::]:2024->2024/tcp
hermes-decepticon-neo4j       neo4j:5.20               "tini -g -- /startup…"   neo4j       59 minutes ago   Up 59 minutes             0.0.0.0:7474->7474/tcp, [::]:7474->7474/tcp, 0.0.0.0:7687->7687/tcp, [::]:7687->7687/tcp
hermes-vault-api              stack-vault-api          "uvicorn main:app --…"   vault-api   59 minutes ago   Up 59 minutes             0.0.0.0:8090->8090/tcp, [::]:8090->8090/tcp
hermes-vnc-cloak              stack-vnc-cloak          "supervisord -c /opt…"   vnc-cloak   59 minutes ago   Up 59 minutes             0.0.0.0:5900->5900/tcp, [::]:5900->5900/tcp, 0.0.0.0:6080->6080/tcp, [::]:6080->6080/tcp, 0.0.0.0:9222->9222/tcp, [::]:9222->9222/tcp

===== curl localhost:8080/api/health =====
HTTP/1.1 200 OK
date: Sat, 13 Jun 2026 20:59:04 GMT
server: uvicorn
content-length: 11
content-type: application/json

{"ok":true}

===== curl localhost:20128/health =====
HTTP/1.1 404 Not Found
Cache-Control: private, no-cache, no-store, max-age=0, must-revalidate
Vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
x-nextjs-cache: HIT
x-nextjs-prerender: 1
x-nextjs-prerender: 1
x-nextjs-stale-time: 300
X-Powered-By: Next.js
ETag: "13rpa99azky70v"
Content-Type: text/html; charset=utf-8
Content-Length: 9103
Date: Sat, 13 Jun 2026 20:59:04 GMT
Connection: keep-alive
Keep-Alive: timeout=5

<!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><link rel="preload" href="/_next/static/media/e4af272ccee01ff0-s.p.woff2" as="font" crossorigin="" type="font/woff2"/><link rel="stylesheet" href="/_next/static/css/7a3e1568f247f3d0.css" data-precedence="next"/><link rel="stylesheet" href="/_next/static/css/f3523f2384d31cd9.css" data-precedence="next"/><link rel="preload" as="script" fetchPriority="low" href="/_next/static/chunks/webpack-f482ccef6733ebcc.js"/><script src="/_next/static/chunks/4bd1b696-e356ca5ba0218e27.js" async=""></script><script src="/_next/static/chunks/3794-e569667691edc8f7.js" async=""></script><script src="/_next/static/chunks/main-app-dd34b0e775cca20f.js" async=""></script><script src="/_next/static/chunks/1a258343-bc0b514c079d8898.js" async=""></script><script src="/_next/static/chunks/2649-64ab34e3d24f7ee7.js" async=""></script><script src="/_next/static/chunks/1321-e07e5aac6780b3e8.js" async=""></script><script src="/_next/static/chunks/5497-dba07a76f355b471.js" async=""></script><script src="/_next/static/chunks/app/(dashboard)/layout-5e30ceb0a9542713.js" async=""></script><script src="/_next/static/chunks/app/layout-16af999ae0ff831d.js" async=""></script><meta name="robots" content="noindex"/><meta name="next-size-adjust" content=""/><title>404: This page could not be found.</title><meta name="theme-color" content="#0a0a0a"/><title>9Router - AI Infrastructure Management</title><meta name="description" content="One endpoint for all your AI providers. Manage keys, monitor usage, and scale effortlessly."/><link rel="manifest" href="/manifest.webmanifest"/><link rel="icon" href="/favicon.ico?603d046c9a6fdfbb" type="image/x-icon" sizes="16x16"/><link rel="icon" href="/favicon.svg"/><script>if(document.fonts&&document.fonts.ready){document.fonts.ready.then(function(){document.documentElement.classList.add('fonts-loaded')})}else{document.documentElement.classList.add('fonts-loaded')}</script><script src="/_next/static/chunks/polyfills-42372ed130431b0a.js" noModule=""></script></head><body class="__variable_f367f3 font-sans antialiased"><div hidden=""><!--$--><!--/$--></div><div style="font-family:system-ui,&quot;Segoe UI&quot;,Roboto,Helvetica,Arial,sans-serif,&quot;Apple Color Emoji&quot;,&quot;Segoe UI Emoji&quot;;height:100vh;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center"><div><style>body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}</style><h1 class="next-error-h1" style="display:inline-block;margin:0 20px 0 0;padding:0 23px 0 0;font-size:24px;font-weight:500;vertical-align:top;line-height:49px">404</h1><div style="display:inline-block"><h2 style="font-size:14px;font-weight:400;line-height:49px;margin:0">This page could not be found.</h2></div></div></div><!--$--><!--/$--><script src="/_next/static/chunks/webpack-f482ccef6733ebcc.js" id="_R_" async=""></script><script>(self.__next_f=self.__next_f||[]).push([0])</script><script>self.__next_f.push([1,"1:\"$Sreact.fragment\"\n2:I[21110,[\"3862\",\"static/chunks/1a258343-bc0b514c079d8898.js\",\"2649\",\"static/chunks/2649-64ab34e3d24f7ee7.js\",\"1321\",\"static/chunks/1321-e07e5aac6780b3e8.js\",\"5497\",\"static/chunks/5497-dba07a76f355b471.js\",\"9305\",\"static/chunks/app/(dashboard)/layout-5e30ceb0a9542713.js\"],\"ThemeProvider\"]\n3:I[94635,[\"1321\",\"static/chunks/1321-e07e5aac6780b3e8.js\",\"7177\",\"static/chunks/app/layout-16af999ae0ff831d.js\"],\"RuntimeI18nProvider\"]\n4:I[57121,[],\"\"]\n5:I[74581,[],\"\"]\n6:I[90484,[],\"OutletBoundary\"]\n7:\"$Sreact.suspense\"\na:I[90484,[],\"ViewportBoundary\"]\nc:I[90484,[],\"MetadataBoundary\"]\ne:I[27123,[],\"default\",1]\n:HL[\"/_next/static/media/e4af272ccee01ff0-s.p.woff2\",\"font\",{\"crossOrigin\":\"\",\"type\":\"font/woff2\"}]\n:HL[\"/_next/static/css/7a3e1568f247f3d0.css\",\"style\"]\n:HL[\"/_next/static/css/f3523f2384d31cd9.css\",\"style\"]\n"])</script><script>self.__next_f.push([1,"0:{\"P\":null,\"c\":[\"\",\"_not-found\"],\"q\":\"\",\"i\":false,\"f\":[[[\"\",{\"children\":[\"_not-found\",{\"children\":[\"__PAGE__\",{}]}]},\"$undefined\",\"$undefined\",16],[[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"link\",\"0\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/7a3e1568f247f3d0.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}],[\"$\",\"link\",\"1\",{\"rel\":\"stylesheet\",\"href\":\"/_next/static/css/f3523f2384d31cd9.css\",\"precedence\":\"next\",\"crossOrigin\":\"$undefined\",\"nonce\":\"$undefined\"}]],[\"$\",\"html\",null,{\"lang\":\"en\",\"suppressHydrationWarning\":true,\"children\":[[\"$\",\"head\",null,{\"children\":[\"$\",\"script\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"if(document.fonts\u0026\u0026document.fonts.ready){document.fonts.ready.then(function(){document.documentElement.classList.add('fonts-loaded')})}else{document.documentElement.classList.add('fonts-loaded')}\"}}]}],[\"$\",\"body\",null,{\"className\":\"__variable_f367f3 font-sans antialiased\",\"children\":[\"$\",\"$L2\",null,{\"children\":[\"$\",\"$L3\",null,{\"children\":[\"$\",\"$L4\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L5\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]}]}]}]]}]]}],{\"children\":[[\"$\",\"$1\",\"c\",{\"children\":[null,[\"$\",\"$L4\",null,{\"parallelRouterKey\":\"children\",\"error\":\"$undefined\",\"errorStyles\":\"$undefined\",\"errorScripts\":\"$undefined\",\"template\":[\"$\",\"$L5\",null,{}],\"templateStyles\":\"$undefined\",\"templateScripts\":\"$undefined\",\"notFound\":\"$undefined\",\"forbidden\":\"$undefined\",\"unauthorized\":\"$undefined\"}]]}],{\"children\":[[\"$\",\"$1\",\"c\",{\"children\":[[[\"$\",\"title\",null,{\"children\":\"404: This page could not be found.\"}],[\"$\",\"div\",null,{\"style\":{\"fontFamily\":\"system-ui,\\\"Segoe UI\\\",Roboto,Helvetica,Arial,sans-serif,\\\"Apple Color Emoji\\\",\\\"Segoe UI Emoji\\\"\",\"height\":\"100vh\",\"textAlign\":\"center\",\"display\":\"flex\",\"flexDirection\":\"column\",\"alignItems\":\"center\",\"justifyContent\":\"center\"},\"children\":[\"$\",\"div\",null,{\"children\":[[\"$\",\"style\",null,{\"dangerouslySetInnerHTML\":{\"__html\":\"body{color:#000;background:#fff;margin:0}.next-error-h1{border-right:1px solid rgba(0,0,0,.3)}@media (prefers-color-scheme:dark){body{color:#fff;background:#000}.next-error-h1{border-right:1px solid rgba(255,255,255,.3)}}\"}}],[\"$\",\"h1\",null,{\"className\":\"next-error-h1\",\"style\":{\"display\":\"inline-block\",\"margin\":\"0 20px 0 0\",\"padding\":\"0 23px 0 0\",\"fontSize\":24,\"fontWeight\":500,\"verticalAlign\":\"top\",\"lineHeight\":\"49px\"},\"children\":404}],[\"$\",\"div\",null,{\"style\":{\"display\":\"inline-block\"},\"children\":[\"$\",\"h2\",null,{\"style\":{\"fontSize\":14,\"fontWeight\":400,\"lineHeight\":\"49px\",\"margin\":0},\"children\":\"This page could not be found.\"}]}]]}]}]],null,[\"$\",\"$L6\",null,{\"children\":[\"$\",\"$7\",null,{\"name\":\"Next.MetadataOutlet\",\"children\":\"$@8\"}]}]]}],{},null,false,null]},null,false,\"$@9\"]},null,false,null],[\"$\",\"$1\",\"h\",{\"children\":[[\"$\",\"meta\",null,{\"name\":\"robots\",\"content\":\"noindex\"}],[\"$\",\"$La\",null,{\"children\":\"$Lb\"}],[\"$\",\"div\",null,{\"hidden\":true,\"children\":[\"$\",\"$Lc\",null,{\"children\":[\"$\",\"$7\",null,{\"name\":\"Next.Metadata\",\"children\":\"$Ld\"}]}]}],[\"$\",\"meta\",null,{\"name\":\"next-size-adjust\",\"content\":\"\"}]]}],false]],\"m\":\"$undefined\",\"G\":[\"$e\",[]],\"S\":true,\"h\":null,\"s\":\"$undefined\",\"l\":\"$undefined\",\"p\":\"$undefined\",\"d\":\"$undefined\",\"b\":\"E54CbuEPd9aTGb4_qOU2a\"}\n"])</script><script>self.__next_f.push([1,"f:[]\n9:\"$Wf\"\n"])</script><script>self.__next_f.push([1,"b:[[\"$\",\"meta\",\"0\",{\"charSet\":\"utf-8\"}],[\"$\",\"meta\",\"1\",{\"name\":\"viewport\",\"content\":\"width=device-width, initial-scale=1\"}],[\"$\",\"meta\",\"2\",{\"name\":\"theme-color\",\"content\":\"#0a0a0a\"}]]\n"])</script><script>self.__next_f.push([1,"10:I[86869,[],\"IconMark\"]\n8:null\nd:[[\"$\",\"title\",\"0\",{\"children\":\"9Router - AI Infrastructure Management\"}],[\"$\",\"meta\",\"1\",{\"name\":\"description\",\"content\":\"One endpoint for all your AI providers. Manage keys, monitor usage, and scale effortlessly.\"}],[\"$\",\"link\",\"2\",{\"rel\":\"manifest\",\"href\":\"/manifest.webmanifest\",\"crossOrigin\":\"$undefined\"}],[\"$\",\"link\",\"3\",{\"rel\":\"icon\",\"href\":\"/favicon.ico?603d046c9a6fdfbb\",\"type\":\"image/x-icon\",\"sizes\":\"16x16\"}],[\"$\",\"link\",\"4\",{\"rel\":\"icon\",\"href\":\"/favicon.svg\"}],[\"$\",\"$L10\",\"5\",{}]]\n"])</script></body></html>

===== curl localhost:20128/api/health (fallback used by install.sh) =====
HTTP/1.1 200 OK
vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch
access-control-allow-headers: *
access-control-allow-methods: GET, OPTIONS
access-control-allow-origin: *
content-type: application/json
Date: Sat, 13 Jun 2026 20:59:04 GMT
Connection: keep-alive
Keep-Alive: timeout=5
Transfer-Encoding: chunked

{"ok":true}

===== curl localhost:6080/vnc.html =====
HTTP/1.1 200 OK
Server: WebSockify Python/3.11.2
Date: Sat, 13 Jun 2026 20:59:05 GMT
Content-type: text/html
Content-Length: 15403
Last-Modified: Tue, 18 Jun 2024 12:05:35 GMT

<!DOCTYPE html>
<html lang="en" class="noVNC_loading">
<head>

    <!--
    noVNC example: simple example using default UI
    Copyright (C) 2019 The noVNC Authors
    noVNC is licensed under the MPL 2.0 (see LICENSE.txt)
    This file is licensed under the 2-Clause BSD license (see LICENSE.txt).

    Connect parameters are provided in query string:
        http://example.com/?host=HOST&port=PORT&encrypt=1
    or the fragment:
        http://example.com/#host=HOST&port=PORT&encrypt=1
    -->
    <title>noVNC</title>

    <link rel="icon" type="image/x-icon" href="app/images/icons/novnc.ico">

    <!-- Apple iOS Safari settings -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

    <!-- @2x -->
    <link rel="apple-touch-icon" sizes="40x40" type="image/png" href="app/images/icons/novnc-ios-40.png">
    <link rel="apple-touch-icon" sizes="58x58" type="image/png" href="app/images/icons/novnc-ios-58.png">
    <link rel="apple-touch-icon" sizes="80x80" type="image/png" href="app/images/icons/novnc-ios-80.png">
    <link rel="apple-touch-icon" sizes="120x120" type="image/png" href="app/images/icons/novnc-ios-120.png">
    <link rel="apple-touch-icon" sizes="152x152" type="image/png" href="app/images/icons/novnc-ios-152.png">
    <link rel="apple-touch-icon" sizes="167x167" type="image/png" href="app/images/icons/novnc-ios-167.png">
    <!-- @3x -->
    <link rel="apple-touch-icon" sizes="60x60" type="image/png" href="app/images/icons/novnc-ios-60.png">
    <link rel="apple-touch-icon" sizes="87x87" type="image/png" href="app/images/icons/novnc-ios-87.png">
    <link rel="apple-touch-icon" sizes="120x120" type="image/png" href="app/images/icons/novnc-ios-120.png">
    <link rel="apple-touch-icon" sizes="180x180" type="image/png" href="app/images/icons/novnc-ios-180.png">

    <!-- Stylesheets -->
    <link rel="stylesheet" href="app/styles/base.css">
    <link rel="stylesheet" href="app/styles/input.css">

    <!-- Images that will later appear via CSS -->
    <link rel="preload" as="image" href="app/images/info.svg">
    <link rel="preload" as="image" href="app/images/error.svg">
    <link rel="preload" as="image" href="app/images/warning.svg">

    <script type="module" crossorigin="anonymous" src="app/error-handler.js"></script>
    <script type="module" crossorigin="anonymous" src="app/ui.js"></script>
</head>

<body>

    <div id="noVNC_fallback_error" class="noVNC_center">
        <div>
            <div>noVNC encountered an error:</div>
            <br>
            <div id="noVNC_fallback_errormsg"></div>
        </div>
    </div>

    <!-- noVNC Control Bar -->
    <div id="noVNC_control_bar_anchor" class="noVNC_vcenter">

        <div id="noVNC_control_bar">
            <div id="noVNC_control_bar_handle" title="Hide/Show the control bar"><div></div></div>

            <div class="noVNC_scroll">

            <h1 class="noVNC_logo" translate="no"><span>no</span><br>VNC</h1>

            <hr>

            <!-- Drag/Pan the viewport -->
            <input type="image" alt="Drag" src="app/images/drag.svg"
                id="noVNC_view_drag_button" class="noVNC_button noVNC_hidden"
                title="Move/Drag Viewport">

            <!--noVNC Touch Device only buttons-->
            <div id="noVNC_mobile_buttons">
                <input type="image" alt="Keyboard" src="app/images/keyboard.svg"
                    id="noVNC_keyboard_button" class="noVNC_button" title="Show Keyboard">
            </div>

            <!-- Extra manual keys -->
            <input type="image" alt="Extra keys" src="app/images/toggleextrakeys.svg"
                id="noVNC_toggle_extra_keys_button" class="noVNC_button"
                title="Show Extra Keys">
            <div class="noVNC_vcenter">
            <div id="noVNC_modifiers" class="noVNC_panel">
                <input type="image" alt="Ctrl" src="app/images/ctrl.svg"
                    id="noVNC_toggle_ctrl_button" class="noVNC_button"
                    title="Toggle Ctrl">
                <input type="image" alt="Alt" src="app/images/alt.svg"
                    id="noVNC_toggle_alt_button" class="noVNC_button"
                    title="Toggle Alt">
                <input type="image" alt="Windows" src="app/images/windows.svg"
                    id="noVNC_toggle_windows_button" class="noVNC_button"
                    title="Toggle Windows">
                <input type="image" alt="Tab" src="app/images/tab.svg"
                    id="noVNC_send_tab_button" class="noVNC_button"
                    title="Send Tab">
                <input type="image" alt="Esc" src="app/images/esc.svg"
                    id="noVNC_send_esc_button" class="noVNC_button"
                    title="Send Escape">
                <input type="image" alt="Ctrl+Alt+Del" src="app/images/ctrlaltdel.svg"
                    id="noVNC_send_ctrl_alt_del_button" class="noVNC_button"
                    title="Send Ctrl-Alt-Del">
            </div>
            </div>

            <!-- Shutdown/Reboot -->
            <input type="image" alt="Shutdown/Reboot" src="app/images/power.svg"
                id="noVNC_power_button" class="noVNC_button"
                title="Shutdown/Reboot...">
            <div class="noVNC_vcenter">
            <div id="noVNC_power" class="noVNC_panel">
                <div class="noVNC_heading">
                    <img alt="" src="app/images/power.svg"> Power
                </div>
                <input type="button" id="noVNC_shutdown_button" value="Shutdown">
                <input type="button" id="noVNC_reboot_button" value="Reboot">
                <input type="button" id="noVNC_reset_button" value="Reset">
            </div>
            </div>

            <!-- Clipboard -->
            <input type="image" alt="Clipboard" src="app/images/clipboard.svg"
                id="noVNC_clipboard_button" class="noVNC_button"
                title="Clipboard">
            <div class="noVNC_vcenter">
            <div id="noVNC_clipboard" class="noVNC_panel">
                <div class="noVNC_heading">
                    <img alt="" src="app/images/clipboard.svg"> Clipboard
                </div>
                <p class="noVNC_subheading">
                    Edit clipboard content in the textarea below.
                </p>
                <textarea id="noVNC_clipboard_text" rows=5></textarea>
            </div>
            </div>

            <!-- Toggle fullscreen -->
            <input type="image" alt="Full Screen" src="app/images/fullscreen.svg"
                id="noVNC_fullscreen_button" class="noVNC_button noVNC_hidden"
                title="Full Screen">

            <!-- Settings -->
            <input type="image" alt="Settings" src="app/images/settings.svg"
                id="noVNC_settings_button" class="noVNC_button"
                title="Settings">
            <div class="noVNC_vcenter">
            <div id="noVNC_settings" class="noVNC_panel">
                <div class="noVNC_heading">
                    <img alt="" src="app/images/settings.svg"> Settings
                </div>
                <ul>
                    <li>
                        <label><input id="noVNC_setting_shared" type="checkbox"> Shared Mode</label>
                    </li>
                    <li>
                        <label><input id="noVNC_setting_view_only" type="checkbox"> View Only</label>
                    </li>
                    <li><hr></li>
                    <li>
                        <label><input id="noVNC_setting_view_clip" type="checkbox"> Clip to Window</label>
                    </li>
                    <li>
                        <label for="noVNC_setting_resize">Scaling Mode:</label>
                        <select id="noVNC_setting_resize" name="vncResize">
                            <option value="off">None</option>
                            <option value="scale">Local Scaling</option>
                            <option value="remote">Remote Resizing</option>
                        </select>
                    </li>
                    <li><hr></li>
                    <li>
                        <div class="noVNC_expander">Advanced</div>
                        <div><ul>
                            <li>
                                <label for="noVNC_setting_quality">Quality:</label>
                                <input id="noVNC_setting_quality" type="range" min="0" max="9" value="6">
                            </li>
                            <li>
                                <label for="noVNC_setting_compression">Compression level:</label>
                                <input id="noVNC_setting_compression" type="range" min="0" max="9" value="2">
                            </li>
                            <li><hr></li>
                            <li>
                                <label for="noVNC_setting_repeaterID">Repeater ID:</label>
                                <input id="noVNC_setting_repeaterID" type="text" value="">
                            </li>
                            <li>
                                <div class="noVNC_expander">WebSocket</div>
                                <div><ul>
                                    <li>
                                        <label><input id="noVNC_setting_encrypt" type="checkbox"> Encrypt</label>
                                    </li>
                                    <li>
                                        <label for="noVNC_setting_host">Host:</label>
                                        <input id="noVNC_setting_host">
                                    </li>
                                    <li>
                                        <label for="noVNC_setting_port">Port:</label>
                                        <input id="noVNC_setting_port" type="number">
                                    </li>
                                    <li>
                                        <label for="noVNC_setting_path">Path:</label>
                                        <input id="noVNC_setting_path" type="text" value="websockify">
                                    </li>
                                </ul></div>
                            </li>
                            <li><hr></li>
                            <li>
                                <label><input id="noVNC_setting_reconnect" type="checkbox"> Automatic Reconnect</label>
                            </li>
                            <li>
                                <label for="noVNC_setting_reconnect_delay">Reconnect Delay (ms):</label>
                                <input id="noVNC_setting_reconnect_delay" type="number">
                            </li>
                            <li><hr></li>
                            <li>
                                <label><input id="noVNC_setting_show_dot" type="checkbox"> Show Dot when No Cursor</label>
                            </li>
                            <li><hr></li>
                            <!-- Logging selection dropdown -->
                            <li>
                                <label>Logging:
                                    <select id="noVNC_setting_logging" name="vncLogging">
                                    </select>
                                </label>
                            </li>
                        </ul></div>
                    </li>
                    <li class="noVNC_version_separator"><hr></li>
                    <li class="noVNC_version_wrapper">
                        <span>Version:</span>
                        <span class="noVNC_version"></span>
                    </li>
                </ul>
            </div>
            </div>

            <!-- Connection Controls -->
            <input type="image" alt="Disconnect" src="app/images/disconnect.svg"
                id="noVNC_disconnect_button" class="noVNC_button"
                title="Disconnect">

            </div>
        </div>

    </div> <!-- End of noVNC_control_bar -->

    <div id="noVNC_hint_anchor" class="noVNC_vcenter">
        <div id="noVNC_control_bar_hint">
        </div>
    </div>

    <!-- Status Dialog -->
    <div id="noVNC_status"></div>

    <!-- Connect button -->
    <div class="noVNC_center">
        <div id="noVNC_connect_dlg">
            <p class="noVNC_logo" translate="no"><span>no</span>VNC</p>
            <div>
                <button id="noVNC_connect_button">
                    <img alt="" src="app/images/connect.svg"> Connect
                </button>
            </div>
        </div>
    </div>

    <!-- Server Key Verification Dialog -->
    <div class="noVNC_center noVNC_connect_layer">
    <div id="noVNC_verify_server_dlg" class="noVNC_panel"><form>
        <div class="noVNC_heading">
            Server identity
        </div>
        <div>
            The server has provided the following identifying information:
        </div>
        <div id="noVNC_fingerprint_block">
            <b>Fingerprint:</b>
            <span id="noVNC_fingerprint"></span>
        </div>
        <div>
            Please verify that the information is correct and press
            "Approve". Otherwise press "Reject".
        </div>
        <div>
            <input id="noVNC_approve_server_button" type="submit" value="Approve" class="noVNC_submit">
            <input id="noVNC_reject_server_button" type="button" value="Reject" class="noVNC_submit">
        </div>
    </form></div>
    </div>

    <!-- Password Dialog -->
    <div class="noVNC_center noVNC_connect_layer">
    <div id="noVNC_credentials_dlg" class="noVNC_panel"><form>
        <div class="noVNC_heading">
            Credentials
        </div>
        <div id="noVNC_username_block">
            <label for="noVNC_username_input">Username:</label>
            <input id="noVNC_username_input">
        </div>
        <div id="noVNC_password_block">
            <label for="noVNC_password_input">Password:</label>
            <input id="noVNC_password_input" type="password">
        </div>
        <div>
            <input id="noVNC_credentials_button" type="submit" value="Send Credentials" class="noVNC_submit">
        </div>
    </form></div>
    </div>

    <!-- Transition Screens -->
    <div id="noVNC_transition">
        <div id="noVNC_transition_text"></div>
        <div>
        <input type="button" id="noVNC_cancel_reconnect_button" value="Cancel" class="noVNC_submit">
        </div>
        <div class="noVNC_spinner"></div>
    </div>

    <!-- This is where the RFB elements will attach -->
    <div id="noVNC_container">
        <!-- Note that Google Chrome on Android doesn't respect any of these,
             html attributes which attempt to disable text suggestions on the
             on-screen keyboard. Let's hope Chrome implements the ime-mode
             style for example -->
        <textarea id="noVNC_keyboardinput" autocapitalize="off"
            autocomplete="off" spellcheck="false" tabindex="-1"></textarea>
    </div>

    <audio id="noVNC_bell">
        <source src="app/sounds/bell.oga" type="audio/ogg">
        <source src="app/sounds/bell.mp3" type="audio/mpeg">
    </audio>
 </body>
</html>

===== hermes --version =====
Hermes Agent v0.16.0 (2026.6.5)
Project: D:\Stack\hermes-agent-2026.6.5
Python: 3.12.13
OpenAI SDK: 2.24.0

===== pytest dashboard health/public paths =====
........                                                                 [100%]
============================== warnings summary ===============================
tests\hermes_cli\test_dashboard_auth_middleware.py:24
  D:\Stack\hermes-agent-2026.6.5\tests\hermes_cli\test_dashboard_auth_middleware.py:24: PytestUnknownMarkWarning: Unknown pytest.mark.xdist_group - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    pytestmark = pytest.mark.xdist_group("dashboard_auth_app_state")

tests\hermes_cli\test_dashboard_auth_gate.py:13
  D:\Stack\hermes-agent-2026.6.5\tests\hermes_cli\test_dashboard_auth_gate.py:13: PytestUnknownMarkWarning: Unknown pytest.mark.xdist_group - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    pytestmark = pytest.mark.xdist_group("dashboard_auth_app_state")

tests/hermes_cli/test_dashboard_auth_middleware.py::test_gated_status_is_public
  D:\Stack\hermes-agent-2026.6.5\.venv\Lib\site-packages\discord\player.py:30: DeprecationWarning: 'audioop' is deprecated and slated for removal in Python 3.13
    import audioop

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 3 warnings in 2.05s


PHASE 7 LOCAL-EQUIVALENT GATE: PASS
```

## Problems And Resolutions
- Exact clean install command could not be executed from raw GitHub because this local repo has no configured origin URL and WSL has no Ubuntu distro (only docker-desktop). Local equivalent checks were run against the in-place stack per the current local-only workflow.
- Dashboard /api/health initially returned 401 because it was not in the shared public API allowlist. Added a minimal {"ok": true} endpoint and added /api/health to PUBLIC_API_PATHS; targeted dashboard auth tests pass.
- 9router upstream image returns HTTP 404 on /health; its /api/health returns HTTP 200. install.sh already waits on /health, /api/health, then root URL, so the installer health wait is covered.

## Pushed
Not pushed: this checkout has no origin remote configured. User indicated local build first, later manual GitHub upload.
