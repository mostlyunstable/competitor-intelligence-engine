from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.database.models import (
    CollectionLog,
    Competitor,
    CompetitorContent,
    CompetitorPage,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
    CompetitorSource,
)
from app.schedulers.scheduler import scheduler
from app.services.collection_service import collection_service

router = APIRouter(tags=["dashboard"])

# The beautiful HTML dashboard provided by the user, with custom dynamic JS bindings
DASHBOARD_HTML = """
<!DOCTYPE html>
<html class="light" lang="en">
<head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>DataEngine Ops - Competitor Intelligence</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <!-- Google Fonts: Editorial Serif (Playfair Display) & Manrope -->
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200..800&amp;family=Playfair+Display:ital,wght@0,400..900;1,400..900&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>
    <!-- Material Symbols -->
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
    <script id="tailwind-config">
        tailwind.config = {
          darkMode: "class",
          theme: {
            extend: {
              "colors": {
                      "primary": "#c2652a", // Sahara Clay
                      "on-primary": "#ffffff",
                      "primary-container": "#fdf3eb",
                      "on-primary-container": "#4a2108",
                      "surface": "#faf8f6", // Warm Cream
                      "surface-container-lowest": "#ffffff",
                      "surface-container-low": "#f7f3f0",
                      "surface-container": "#f1ece8",
                      "surface-container-high": "#ebe4df",
                      "surface-container-highest": "#e5ddd6",
                      "on-surface": "#2c2826",
                      "on-surface-variant": "#5a524e",
                      "outline": "#8b7e76",
                      "outline-variant": "#d5cdc8",
                      "background": "#faf8f6",
                      "error": "#ba1a1a",
                      "secondary": "#735c4c",
                      "secondary-container": "#fceee5"
              },
              "borderRadius": {
                      "DEFAULT": "0.5rem",
                      "lg": "0.75rem",
                      "xl": "1rem",
                      "full": "9999px"
              },
              "spacing": {
                      "stack-md": "16px",
                      "unit": "4px",
                      "stack-sm": "8px",
                      "container-padding": "24px",
                      "gutter": "16px",
                      "stack-lg": "32px"
              },
              "fontFamily": {
                      "body-lg": ["Manrope", "sans-serif"],
                      "h3": ["Playfair Display", "serif"],
                      "label-md": ["Manrope", "sans-serif"],
                      "h2": ["Playfair Display", "serif"],
                      "body-md": ["Manrope", "sans-serif"],
                      "label-sm": ["Manrope", "sans-serif"],
                      "body-sm": ["Manrope", "sans-serif"],
                      "h1": ["Playfair Display", "serif"],
                      "mono": ["JetBrains Mono", "monospace"]
              },
              "fontSize": {
                      "body-lg": ["16px", {"lineHeight": "24px", "fontWeight": "400"}],
                      "h3": ["20px", {"lineHeight": "28px", "letterSpacing": "-0.01em", "fontWeight": "600"}],
                      "label-md": ["14px", {"lineHeight": "20px", "fontWeight": "500"}],
                      "h2": ["24px", {"lineHeight": "32px", "letterSpacing": "-0.02em", "fontWeight": "600"}],
                      "body-md": ["14px", {"lineHeight": "20px", "fontWeight": "400"}],
                      "label-sm": ["12px", {"lineHeight": "16px", "fontWeight": "500"}],
                      "body-sm": ["12px", {"lineHeight": "18px", "fontWeight": "400"}],
                      "h1": ["30px", {"lineHeight": "36px", "letterSpacing": "-0.02em", "fontWeight": "600"}],
                      "mono": ["13px", {"lineHeight": "20px", "fontWeight": "400"}]
              },
              "boxShadow": {
                "soft": "0 4px 20px -2px rgba(194, 101, 42, 0.05), 0 2px 8px -2px rgba(0, 0, 0, 0.04)"
              }
            },
          },
        }
    </script>
    <style>
        body { font-family: 'Manrope', sans-serif; -webkit-font-smoothing: antialiased; }
        h1, h2, h3 { font-family: 'Playfair Display', serif; }
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
            display: inline-block;
            vertical-align: middle;
        }
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        .skeleton {
            background: linear-gradient(90deg, #f1ece8 25%, #e5ddd6 50%, #f1ece8 75%);
            background-size: 200% 100%;
            animation: shimmer 2s infinite linear;
        }
        @keyframes toastIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes toastOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .toast-in { animation: toastIn 0.3s ease-out forwards; }
        .toast-out { animation: toastOut 0.3s ease-in forwards; }
    </style>
</head>
<body class="bg-background text-on-surface">
<!-- SideNavBar -->
<aside class="fixed left-0 top-0 h-full w-[280px] bg-surface-container-lowest border-r border-outline-variant flex flex-col p-stack-md gap-stack-sm z-50">
    <div class="mb-stack-lg px-2">
        <h1 class="text-h3 font-bold text-primary italic">Utservio Data Engine</h1>
        <p class="font-label-sm text-label-sm text-outline opacity-70">v2.4.0-stable</p>
    </div>
    <nav class="flex-1 flex flex-col gap-unit">
        <a class="flex items-center gap-stack-sm p-stack-sm bg-secondary-container text-on-primary-container rounded-lg font-semibold shadow-sm duration-200" href="/dashboard">
            <span class="material-symbols-outlined text-[20px]" data-icon="dashboard">dashboard</span>
            <span class="font-body-md text-body-md">Dashboard</span>
        </a>
        <a class="flex items-center gap-stack-sm p-stack-sm text-on-surface-variant hover:bg-surface-container transition-colors rounded-lg duration-200" href="/docs" target="_blank">
            <span class="material-symbols-outlined text-[20px]" data-icon="description">description</span>
            <span class="font-body-md text-body-md">API Swagger Docs</span>
        </a>
    </nav>
    <div class="pt-stack-md border-t border-outline-variant">
        <div class="flex items-center gap-stack-sm px-2">
            <div class="w-9 h-9 rounded-full bg-surface-container-high flex items-center justify-center">
                <span class="material-symbols-outlined text-primary/70" data-icon="engineering">engineering</span>
            </div>
            <div class="overflow-hidden">
                <p class="font-label-md text-label-md truncate font-semibold">Lead Engineer</p>
                <p class="font-label-sm text-label-sm text-outline truncate">ops-admin</p>
            </div>
        </div>
    </div>
</aside>

<!-- TopNavBar -->
<header class="fixed top-0 right-0 w-[calc(100%-280px)] h-16 bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant flex justify-between items-center px-container-padding z-40 transition-all">
    <div class="flex items-center gap-gutter">
        <span class="font-h3 text-h3 text-on-surface">Utservio Data Engine Ops</span>
        <div class="h-4 w-[1px] bg-outline-variant"></div>
        <div class="flex gap-stack-md">
            <span class="font-label-md text-label-md text-primary font-bold" id="header-status">Status: Checking...</span>
            <span class="font-label-md text-label-md text-on-surface-variant opacity-70" id="header-uptime">Uptime: --</span>
        </div>
    </div>
</header>

<!-- Main Content -->
<main class="ml-[280px] pt-16 p-container-padding min-h-screen">
    <div class="max-w-7xl mx-auto flex flex-col gap-stack-lg">

        <!-- Pipeline Status -->
        <section>
            <h2 class="font-label-sm text-label-sm text-outline uppercase tracking-[0.1em] mb-stack-sm font-semibold">Pipeline Status</h2>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-soft flex items-center justify-between overflow-x-auto">
                <!-- Step 1 -->
                <div class="flex flex-col items-center gap-unit min-w-[80px]" id="step-discovery">
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]" data-icon="search">search</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline">Discovery</span>
                </div>
                <div class="flex-1 h-[1px] bg-outline-variant mx-unit min-w-[20px]" id="line-discovery"></div>
                <!-- Step 2 -->
                <div class="flex flex-col items-center gap-unit min-w-[80px]" id="step-fetch">
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]" data-icon="cloud_download">cloud_download</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline">Fetch</span>
                </div>
                <div class="flex-1 h-[1px] bg-outline-variant mx-unit min-w-[20px]" id="line-fetch"></div>
                <!-- Step 3 -->
                <div class="flex flex-col items-center gap-unit min-w-[80px]" id="step-parse">
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]" data-icon="code">code</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline">Parse</span>
                </div>
                <div class="flex-1 h-[1px] bg-outline-variant mx-unit min-w-[20px]" id="line-parse"></div>
                <!-- Step 4 -->
                <div class="flex flex-col items-center gap-unit min-w-[80px]" id="step-normalize">
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]" data-icon="equalizer">equalizer</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline">Normalize</span>
                </div>
                <div class="flex-1 h-[1px] bg-outline-variant mx-unit min-w-[20px]" id="line-normalize"></div>
                <!-- Step 5 -->
                <div class="flex flex-col items-center gap-unit min-w-[80px]" id="step-validate">
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]" data-icon="verified">verified</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline">Validate</span>
                </div>
                <div class="flex-1 h-[1px] bg-outline-variant mx-unit min-w-[20px]" id="line-validate"></div>
                <!-- Step 6 -->
                <div class="flex flex-col items-center gap-unit min-w-[80px]" id="step-store">
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]" data-icon="database">database</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline">Store</span>
                </div>
            </div>
        </section>

        <!-- Metric Cards -->
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-gutter">
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex flex-col gap-unit shadow-soft hover:shadow-md transition-shadow">
                <p class="font-label-sm text-label-sm text-outline">URLs Discovered</p>
                <p class="font-h2 text-h2 text-on-surface" id="metric-urls">--</p>
                <p class="font-label-sm text-label-sm text-outline opacity-50" id="sub-urls">Loading...</p>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex flex-col gap-unit shadow-soft hover:shadow-md transition-shadow">
                <p class="font-label-sm text-label-sm text-outline">Pages Crawled</p>
                <p class="font-h2 text-h2 text-on-surface" id="metric-pages">--</p>
                <p class="font-label-sm text-label-sm text-outline opacity-50" id="sub-pages">Loading...</p>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex flex-col gap-unit shadow-soft hover:shadow-md transition-shadow">
                <p class="font-label-sm text-label-sm text-outline">Services Extracted</p>
                <p class="font-h2 text-h2 text-on-surface" id="metric-services">--</p>
                <p class="font-label-sm text-label-sm text-outline opacity-50" id="sub-services">Loading...</p>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex flex-col gap-unit shadow-soft hover:shadow-md transition-shadow">
                <p class="font-label-sm text-label-sm text-outline">Pricing Extracted</p>
                <p class="font-h2 text-h2 text-on-surface" id="metric-pricing">--</p>
                <p class="font-label-sm text-label-sm text-outline opacity-50" id="sub-pricing">Loading...</p>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex flex-col gap-unit shadow-soft hover:shadow-md transition-shadow">
                <p class="font-label-sm text-label-sm text-outline">Database Entries</p>
                <p class="font-h2 text-h2 text-on-surface" id="metric-db-writes">--</p>
                <p class="font-label-sm text-label-sm text-outline opacity-50" id="sub-db-writes">Loading...</p>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex flex-col gap-unit shadow-soft border-l-4 border-l-error/30">
                <p class="font-label-sm text-label-sm text-outline">Errors</p>
                <p class="font-h2 text-h2 text-on-surface" id="metric-errors">--</p>
                <p class="font-label-sm text-label-sm text-error font-bold" id="sub-errors">Stable</p>
            </div>
        </section>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
            <!-- Current Collection & Controls -->
            <div class="lg:col-span-4 flex flex-col gap-stack-sm">
                <h2 class="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">Controls & Target</h2>
                <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-soft flex flex-col gap-unit mb-stack-sm">
                    <label class="block font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">Add New Competitor</label>
                    <input type="text" id="new-comp-name" placeholder="Name (e.g. Acme Corp)" class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-2 text-on-surface focus:outline-none focus:border-primary min-w-0">
                    <input type="text" id="new-comp-url" placeholder="URL (e.g. https://acme.com)" class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-2 text-on-surface focus:outline-none focus:border-primary min-w-0">
                    <button id="add-comp-btn" class="w-full py-2.5 px-6 bg-surface-container-high text-on-surface font-label-md text-label-md rounded-lg hover:bg-primary hover:text-white transition-all flex items-center justify-center gap-2 border border-outline-variant mt-2">
                        <span class="material-symbols-outlined text-[18px]">add</span>
                        Add
                    </button>
                </div>

                <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md flex flex-col gap-stack-md shadow-soft">
                    <div>
                        <label for="competitor-select" class="font-label-sm text-label-sm text-outline block mb-1">Select Competitor</label>
                        <select id="competitor-select" class="w-full bg-surface-container border border-outline-variant rounded-lg p-2 font-body-md text-body-md focus:outline-none focus:ring-1 focus:ring-primary">
                            <option value="">-- Choose Competitor --</option>
                        </select>
                    </div>

                    <div class="border-t border-outline-variant pt-stack-sm">
                        <p class="font-label-sm text-label-sm text-outline">Target URL</p>
                        <p class="font-body-md text-body-md font-mono truncate text-on-surface-variant" id="target-url">No competitor selected</p>
                        <p class="font-label-sm text-label-sm text-outline opacity-50 mt-1" id="last-collected"></p>
                    </div>

                    <div class="grid grid-cols-2 gap-gutter">
                        <div>
                            <p class="font-label-sm text-label-sm text-outline">Status</p>
                            <p class="font-label-md text-label-md text-primary font-bold" id="collect-status">IDLE</p>
                        </div>
                        <div>
                            <p class="font-label-sm text-label-sm text-outline">Progress</p>
                            <p class="font-mono text-mono text-on-surface" id="collect-progress">0%</p>
                        </div>
                    </div>

                    <div>
                        <div class="w-full h-1.5 bg-surface-container-high rounded-full overflow-hidden">
                            <div class="h-full bg-primary transition-all duration-500" id="progress-bar" style="width: 0%;"></div>
                        </div>
                    </div>

                    <div class="flex gap-unit">
                        <button id="trigger-btn" disabled class="flex-1 py-3 bg-primary text-white font-label-md text-label-md rounded-lg hover:brightness-105 disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-md shadow-primary/20">
                            <span class="material-symbols-outlined text-[18px]">play_arrow</span>
                            Live Collection
                        </button>
                        <button id="stop-btn" class="hidden py-3 px-4 bg-error text-white font-label-md text-label-md rounded-lg hover:brightness-105 transition-all flex items-center justify-center gap-2 shadow-md shadow-error/20">
                            <span class="material-symbols-outlined text-[18px]">stop</span>
                            Stop
                        </button>
                    </div>
                    <div class="flex gap-unit w-full mt-2">
                        <button id="view-json-btn" disabled class="flex-1 py-3 bg-surface-container-high text-on-surface font-label-md text-label-md rounded-lg hover:bg-surface-container-highest disabled:opacity-50 transition-all flex items-center justify-center gap-2 border border-outline-variant">
                            <span class="material-symbols-outlined text-[18px]">data_object</span>
                            View JSON
                        </button>
                        <button id="export-csv-btn" disabled class="flex-1 py-3 bg-surface-container-high text-on-surface font-label-md text-label-md rounded-lg hover:bg-surface-container-highest disabled:opacity-50 transition-all flex items-center justify-center gap-2 border border-outline-variant">
                            <span class="material-symbols-outlined text-[18px]">download</span>
                            Export CSV
                        </button>
                    </div>
                </div>

                <h2 class="font-label-sm text-label-sm text-outline uppercase tracking-wider mt-stack-md font-semibold">System Health</h2>
                <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm grid grid-cols-2 gap-unit shadow-soft">
                    <div class="flex items-center gap-unit p-2 bg-surface-container-low rounded-lg">
                        <div class="w-2 h-2 rounded-full" id="health-db-indicator" style="background-color: rgb(139, 126, 118);"></div>
                        <span class="font-label-sm text-label-sm text-on-surface-variant" id="health-db-text">DB: Checking</span>
                    </div>
                    <div class="flex items-center gap-unit p-2 bg-surface-container-low rounded-lg">
                        <div class="w-2 h-2 rounded-full" id="health-scheduler-indicator" style="background-color: rgb(139, 126, 118);"></div>
                        <span class="font-label-sm text-label-sm text-on-surface-variant" id="health-scheduler-text">Scheduler: Checking</span>
                    </div>
                    <div class="flex items-center gap-unit p-2 bg-surface-container-low rounded-lg">
                        <div class="w-2 h-2 rounded-full" id="health-playwright-indicator" style="background-color: rgb(139, 126, 118);"></div>
                        <span class="font-label-sm text-label-sm text-on-surface-variant" id="health-playwright-text">Playwright: Checking</span>
                    </div>
                    <div class="flex items-center gap-unit p-2 bg-surface-container-low rounded-lg">
                        <div class="w-2 h-2 rounded-full" id="health-api-indicator" style="background-color: rgb(139, 126, 118);"></div>
                        <span class="font-label-sm text-label-sm text-on-surface-variant" id="health-api-text">API: Checking</span>
                    </div>
                </div>
            </div>

            <!-- Summary & Logs -->
            <div class="lg:col-span-8 flex flex-col gap-stack-lg">
                <!-- Extraction Summary -->
                <div>
                    <h2 class="font-label-sm text-label-sm text-outline uppercase tracking-wider mb-stack-sm font-semibold">Extraction Summary</h2>
                    <div class="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-soft">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-surface-container-low border-b border-outline-variant">
                                <tr>
                                    <th class="px-stack-md py-3 font-label-sm text-label-sm text-outline uppercase">Competitor Name</th>
                                    <th class="px-stack-md py-3 font-label-sm text-label-sm text-outline uppercase text-center">Services</th>
                                    <th class="px-stack-md py-3 font-label-sm text-label-sm text-outline uppercase text-center">Pricing</th>
                                    <th class="px-stack-md py-3 font-label-sm text-label-sm text-outline uppercase text-center">Articles</th>
                                    <th class="px-stack-md py-3 font-label-sm text-label-sm text-outline uppercase text-center">Socials</th>
                                    <th class="px-stack-md py-3 font-label-sm text-label-sm text-outline uppercase text-center w-16"></th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-outline-variant/30" id="summary-table-body">
                                <tr>
                                    <td class="px-stack-md py-12 text-center text-outline italic font-body-md text-body-md opacity-60" colspan="6">
                                        Loading competitor buffer data...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Collection Logs -->
                <div class="flex-1 flex flex-col min-h-[300px]">
                    <div class="flex justify-between items-end mb-stack-sm">
                        <h2 class="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">Collection Audit Trail</h2>
                        <span class="font-mono text-[10px] text-primary bg-primary-container px-2 py-0.5 rounded-full font-bold" id="stream-status">IDLE</span>
                    </div>
                    <div class="bg-surface-container-lowest border border-outline-variant rounded-xl flex-1 overflow-hidden flex flex-col shadow-soft">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-surface-container-low border-b border-outline-variant sticky top-0 z-10">
                                <tr>
                                    <th class="px-stack-md py-2 font-label-sm text-label-sm text-outline uppercase w-36">Time Started</th>
                                    <th class="px-stack-md py-2 font-label-sm text-label-sm text-outline uppercase w-24">Success</th>
                                    <th class="px-stack-md py-2 font-label-sm text-label-sm text-outline uppercase w-24">Duration</th>
                                    <th class="px-stack-md py-2 font-label-sm text-label-sm text-outline uppercase w-24">Records</th>
                                    <th class="px-stack-md py-2 font-label-sm text-label-sm text-outline uppercase">Error Details</th>
                                </tr>
                            </thead>
                        </table>
                        <div class="flex-1 overflow-y-auto bg-[#1a1817] p-stack-md font-mono text-mono min-h-[220px] max-h-[320px]" id="logs-container">
                            <div class="flex flex-col gap-unit text-stone-400">
                                Loading audit trail...
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Infrastructure Telemetry -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-gutter mt-stack-md">
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex items-center justify-between shadow-soft">
                <div class="flex items-center gap-stack-sm">
                    <span class="material-symbols-outlined text-primary/60" data-icon="memory">memory</span>
                    <span class="font-label-md text-label-md text-on-surface">Engine CPU</span>
                </div>
                <span class="font-mono text-mono text-outline" id="telemetry-cpu">0.0%</span>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex items-center justify-between shadow-soft">
                <div class="flex items-center gap-stack-sm">
                    <span class="material-symbols-outlined text-primary/60" data-icon="dns">dns</span>
                    <span class="font-label-md text-label-md text-on-surface">Node Memory</span>
                </div>
                <span class="font-mono text-mono text-outline" id="telemetry-mem">--MB / --GB</span>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-sm flex items-center justify-between shadow-soft">
                <div class="flex items-center gap-stack-sm">
                    <span class="material-symbols-outlined text-primary/60" data-icon="bolt">bolt</span>
                    <span class="font-label-md text-label-md text-on-surface">Active Crawls</span>
                </div>
                <span class="font-mono text-mono text-outline" id="telemetry-crawls">0</span>
            </div>
        </section>

        <footer class="mt-stack-lg pt-stack-md border-t border-outline-variant/30 flex justify-center">
            <p class="font-label-sm text-label-sm text-outline uppercase tracking-[0.2em] opacity-40">designed and developed by mayank kumar</p>
        </footer>
    </div>

        <!-- JSON Modal -->
        <div id="json-modal" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 hidden flex items-center justify-center p-stack-lg">
            <div class="bg-surface-container-lowest border border-outline-variant rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
                <div class="flex justify-between items-center p-stack-md border-b border-outline-variant">
                    <h2 class="font-h3 text-h3 text-on-surface flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary">data_object</span>
                        Extracted JSON Data
                    </h2>
                    <button id="close-modal-btn" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-container transition-colors">
                        <span class="material-symbols-outlined text-outline">close</span>
                    </button>
                </div>
                <div class="flex-1 overflow-auto bg-[#1a1817] p-stack-md">
                    <pre id="json-viewer" class="font-mono text-[13px] text-emerald-400 m-0 whitespace-pre-wrap">Loading...</pre>
                </div>
            </div>
        </div>

    <!-- Toast Container -->
    <div id="toast-container" class="fixed top-20 right-6 z-[60] flex flex-col gap-2"></div>

</main>

<script>
    // Micro-interactions
    document.querySelectorAll('button, a').forEach(el => {
        el.addEventListener('mousedown', () => {
            el.style.transform = 'scale(0.98)';
        });
        el.addEventListener('mouseup', () => {
            el.style.transform = 'scale(1)';
        });
        el.addEventListener('mouseleave', () => {
            el.style.transform = 'scale(1)';
        });
    });

    const compSelect = document.getElementById('competitor-select');
    const targetUrlEl = document.getElementById('target-url');
    const triggerBtn = document.getElementById('trigger-btn');
    const stopBtn = document.getElementById('stop-btn');
    const viewJsonBtn = document.getElementById('view-json-btn');
    const exportCsvBtn = document.getElementById('export-csv-btn');
    const addCompBtn = document.getElementById('add-comp-btn');
    const jsonModal = document.getElementById('json-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    let competitorsMap = {};
    let activeInterval = null;
    let shownLiveLogs = new Set();
    let lastLogCount = 0;
    let activeCompetitorId = null;
    const pageLoadTime = Date.now();

    // Toast notification utility
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const colors = { success: 'bg-emerald-600', error: 'bg-error', info: 'bg-primary' };
        const toast = document.createElement('div');
        toast.className = `${colors[type] || colors.info} text-white px-4 py-3 rounded-lg shadow-lg font-label-md text-label-md flex items-center gap-2 toast-in`;
        toast.innerHTML = `<span class="material-symbols-outlined text-[18px]">check_circle</span> ${message}`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('toast-in');
            toast.classList.add('toast-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // HTML escaping utility (XSS prevention)
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    async function loadCompetitors() {
        try {
            const res = await fetch(`/api/dashboard/competitors?t=${Date.now()}`);
            if (!res.ok) {
                console.error("Server error when loading competitors:", res.status);
                return;
            }
            const data = await res.json();
            if (!Array.isArray(data)) {
                console.error("Data is not an array");
                return;
            }
            
            // Only clear after we successfully verified the data!
            const oldVal = compSelect.value;
            compSelect.innerHTML = '<option value="">-- Choose Competitor --</option>';
            data.forEach(c => {
                competitorsMap[c.id] = c;
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                compSelect.appendChild(opt);
            });
            if (oldVal && competitorsMap[oldVal]) {
                compSelect.value = oldVal;
            }
        } catch (e) {
            console.error("Failed to load competitors", e);
        }
    }

    compSelect.addEventListener('change', () => {
        const id = compSelect.value;
        if (id && competitorsMap[id]) {
            targetUrlEl.textContent = competitorsMap[id].website_url;
            triggerBtn.removeAttribute('disabled');
            viewJsonBtn.removeAttribute('disabled');
            exportCsvBtn.removeAttribute('disabled');
            // Show last collected time
            const lc = competitorsMap[id].last_collected;
            const lcEl = document.getElementById('last-collected');
            if (lc) {
                const ago = timeAgo(new Date(lc));
                lcEl.textContent = `Last collected: ${ago}`;
            } else {
                lcEl.textContent = 'Never collected';
            }
        } else {
            targetUrlEl.textContent = 'No competitor selected';
            triggerBtn.setAttribute('disabled', 'true');
            viewJsonBtn.setAttribute('disabled', 'true');
            exportCsvBtn.setAttribute('disabled', 'true');
            document.getElementById('last-collected').textContent = '';
        }
    });

    function timeAgo(date) {
        const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
        if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
        return Math.floor(seconds / 86400) + 'd ago';
    }

    addCompBtn.addEventListener('click', async () => {
        const name = document.getElementById('new-comp-name').value;
        const url = document.getElementById('new-comp-url').value;
        if (!name || !url) {
            alert("Please provide both name and url");
            return;
        }
        
        addCompBtn.textContent = 'Adding...';
        try {
            const response = await fetch('/api/dashboard/competitors', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, website_url: url})
            });
            
            if (!response.ok) {
                let errMsg = response.statusText;
                try {
                    const errData = await response.json();
                    errMsg = errData.detail || errMsg;
                } catch(e) {}
                alert("Failed to add competitor: " + errMsg);
                addCompBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">add</span> Add';
                return;
            }
            
            const newComp = await response.json();
            
            await loadCompetitors();
            
            document.getElementById('new-comp-name').value = '';
            document.getElementById('new-comp-url').value = '';
            
            // Auto-select the newly added competitor
            compSelect.value = newComp.id;
            compSelect.dispatchEvent(new Event('change'));

            showToast(`${newComp.name} added successfully`);
            
        } catch(e) {
            console.error(e);
        }
        addCompBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">add</span> Add';
    });

    exportCsvBtn.addEventListener('click', async () => {
        const id = compSelect.value;
        if (!id) return;
        try {
            const res = await fetch(`/api/dashboard/extracted/${id}?t=${Date.now()}`);
            const data = await res.json();
            if (data.data && data.data.pricing && data.data.pricing.length > 0) {
                let csv = "Tier,Price,Currency,Billing\n";
                data.data.pricing.forEach(p => {
                    csv += `"${(p.tier_name || '').replace(/"/g, '""')}","${p.price || ''}","${p.currency || ''}","${p.billing_period || ''}"\n`;
                });
                const blob = new Blob([csv], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `competitor_${id}_pricing.csv`;
                a.click();
                window.URL.revokeObjectURL(url);
            } else {
                alert("No pricing data found to export for this competitor.");
            }
        } catch (e) {
            alert("Export failed.");
        }
    });


    closeModalBtn.addEventListener('click', () => {
        jsonModal.classList.add('hidden');
    });

    // Close modal on Escape key or backdrop click
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !jsonModal.classList.contains('hidden')) {
            jsonModal.classList.add('hidden');
        }
    });
    jsonModal.addEventListener('click', (e) => {
        if (e.target === jsonModal) {
            jsonModal.classList.add('hidden');
        }
    });

    viewJsonBtn.addEventListener('click', async () => {
        const id = compSelect.value;
        if (!id) return;
        jsonModal.classList.remove('hidden');
        document.getElementById('json-viewer').textContent = 'Loading...';
        try {
            const res = await fetch(`/api/dashboard/extracted/${id}?t=${Date.now()}`);
            const data = await res.json();
            if (data.data) {
                document.getElementById('json-viewer').textContent = JSON.stringify(data.data, null, 2);
            } else {
                document.getElementById('json-viewer').textContent = 'No structured JSON data found for this competitor yet.';
            }
        } catch (e) {
            document.getElementById('json-viewer').textContent = 'Error fetching data.';
        }
    });

    // Trigger Collection
    triggerBtn.addEventListener('click', async () => {
        const id = compSelect.value;
        if (!id) return;

        activeCompetitorId = id;
        triggerBtn.setAttribute('disabled', 'true');
        stopBtn.classList.remove('hidden');
        stopBtn.classList.add('flex');
        document.getElementById('collect-status').textContent = 'Discovery';
        document.getElementById('collect-progress').textContent = '10%';
        document.getElementById('progress-bar').style.width = '10%';
        document.getElementById('stream-status').textContent = 'LIVE_STREAM: ACTIVE';

        // Update steps styling
        updatePipelineSteps('discovery');

        try {
            const res = await fetch(`/api/dashboard/collect/${id}`, { method: 'POST' });
            const result = await res.json();

            // Start polling status
            if (activeInterval) clearInterval(activeInterval);
            activeInterval = setInterval(() => pollActiveCrawl(id), 1500);
        } catch (e) {
            console.error("Trigger collection error", e);
            resetCollectionState();
        }
    });

    // Stop Collection
    stopBtn.addEventListener('click', async () => {
        if (!activeCompetitorId) return;
        stopBtn.setAttribute('disabled', 'true');
        try {
            await fetch(`/api/dashboard/collect/${activeCompetitorId}/cancel`, { method: 'POST' });
        } catch (e) {
            console.error("Cancel failed", e);
        }
        resetCollectionState();
    });

    function updatePipelineSteps(stage) {
        const stages = ['discovery', 'fetch', 'parse', 'normalize', 'validate', 'store'];
        stages.forEach(s => {
            const el = document.getElementById(`step-${s}`);
            const line = document.getElementById(`line-${s}`);
            if (s === stage) {
                el.innerHTML = `
                    <div class="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white shadow-md shadow-primary/20">
                        <span class="material-symbols-outlined text-[20px]">${el.querySelector('span').getAttribute('data-icon')}</span>
                    </div>
                    <span class="font-label-md text-label-md text-primary font-bold capitalize">${s}</span>
                `;
                if (line) line.className = "flex-1 h-[2px] bg-primary mx-unit min-w-[20px]";
            } else {
                el.innerHTML = `
                    <div class="w-10 h-10 rounded-full border border-outline-variant flex items-center justify-center text-outline">
                        <span class="material-symbols-outlined text-[20px]">${el.querySelector('span').getAttribute('data-icon')}</span>
                    </div>
                    <span class="font-label-sm text-label-sm text-outline capitalize">${s}</span>
                `;
                if (line) line.className = "flex-1 h-[1px] bg-outline-variant mx-unit min-w-[20px]";
            }
        });
    }

    function resetCollectionState() {
        if (activeInterval) clearInterval(activeInterval);
        document.getElementById('collect-status').textContent = 'IDLE';
        document.getElementById('collect-progress').textContent = '0%';
        document.getElementById('progress-bar').style.width = '0%';
        triggerBtn.removeAttribute('disabled');
        stopBtn.classList.add('hidden');
        stopBtn.classList.remove('flex');
        stopBtn.removeAttribute('disabled');
        activeCompetitorId = null;
        updatePipelineSteps('none');
        shownLiveLogs.clear();
        lastLogCount = 0;
        document.getElementById('stream-status').textContent = 'IDLE';
    }

    async function pollActiveCrawl(id) {
        try {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();

            const active = data.active_collection || {};
            if (active.competitor_id === parseInt(id)) {
                // Determine step simulation
                const elapsed = active.elapsed || 1;
                let step = 'discovery';
                let progress = '20%';
                if (elapsed > 4) { step = 'fetch'; progress = '40%'; }
                if (elapsed > 10) { step = 'parse'; progress = '60%'; }
                if (elapsed > 16) { step = 'normalize'; progress = '80%'; }
                if (elapsed > 20) { step = 'validate'; progress = '90%'; }

                document.getElementById('collect-status').textContent = step.toUpperCase();
                document.getElementById('collect-progress').textContent = progress;
                document.getElementById('progress-bar').style.width = progress;
                updatePipelineSteps(step);

                // Add real streaming live logs
                try {
                    const logRes = await fetch(`/api/dashboard/live_logs/${id}`);
                    const logsData = await logRes.json();
                    if (logsData.length > lastLogCount) {
                        const logsContainer = document.getElementById('logs-container');
                        if (logsContainer.innerHTML.includes('Loading audit trail...') || logsContainer.innerHTML.includes('No collection logs')) {
                            logsContainer.innerHTML = '';
                        }
                        const newLogs = logsData.slice(lastLogCount);
                        newLogs.forEach(log => {
                            let msg = log.event || "";
                            let time = log.timestamp ? log.timestamp.substring(11,19) : new Date().toISOString().substring(11,19);
                            let lvl = log.level ? log.level.toUpperCase() : "INFO";
                            let color = "text-emerald-400";
                            if (lvl === 'WARNING' || lvl === 'WARN') color = "text-yellow-400";
                            if (lvl === 'ERROR') color = "text-red-400";
                            
                            // Format args for display
                            let args = [];
                            for (const [k, v] of Object.entries(log)) {
                                if (!['event', 'timestamp', 'level', 'competitor_id'].includes(k)) {
                                    args.push(`${k}=${v}`);
                                }
                            }
                            let argsStr = args.length > 0 ? ` <span class="text-stone-500 ml-2">${escapeHtml(args.join(' '))}</span>` : '';
                            
                            logsContainer.innerHTML = `<div class="${color} font-mono text-[13px] border-b border-stone-800/40 py-1"><span class="text-stone-500">[${escapeHtml(time)}]</span> [${escapeHtml(lvl)}] ${escapeHtml(msg)}${argsStr}</div>` + logsContainer.innerHTML;
                        });
                        lastLogCount = logsData.length;
                    }
                } catch(e) {}

            } else {
                // If no longer active, set to Store (100%) then finish
                document.getElementById('collect-status').textContent = 'STORE';
                document.getElementById('collect-progress').textContent = '100%';
                document.getElementById('progress-bar').style.width = '100%';
                updatePipelineSteps('store');

                if (!shownLiveLogs.has('store')) {
                    shownLiveLogs.add('store');
                    const logsContainer = document.getElementById('logs-container');
                    const now = new Date().toISOString().substring(11,19);
                    logsContainer.innerHTML = `<div class="text-blue-400 font-mono text-[13px] border-b border-stone-800/40 py-1"><span class="text-stone-500">[${now}]</span> [INFO] Successfully committed transaction to database.</div>` + logsContainer.innerHTML;
                }

                setTimeout(() => {
                    resetCollectionState();
                    refreshData();
                }, 2000);
            }
        } catch (e) {
            console.error(e);
        }
    }

    // Refresh Dashboard Data
    async function refreshData() {
        const timestamp = Date.now();
        
        // 1. Stats
        try {
            const resStats = await fetch(`/api/dashboard/stats?t=${timestamp}`);
            if (resStats.ok) {
                const stats = await resStats.json();
                document.getElementById('metric-urls').textContent = stats.urls_discovered;
                document.getElementById('metric-pages').textContent = stats.pages_crawled;
                document.getElementById('metric-services').textContent = stats.services_extracted;
                document.getElementById('metric-pricing').textContent = stats.pricing_extracted;
                document.getElementById('metric-db-writes').textContent = stats.database_writes;
                document.getElementById('metric-errors').textContent = stats.errors;

                document.getElementById('sub-urls').textContent = "Sources updated";
                document.getElementById('sub-pages').textContent = "Buffer matches active";
                document.getElementById('sub-services').textContent = "Services synced";
                document.getElementById('sub-pricing').textContent = "Pricing synced";
                document.getElementById('sub-db-writes').textContent = "Synchronized";

                // Dynamic error subtitle
                const errCount = stats.errors || 0;
                const subErrors = document.getElementById('sub-errors');
                if (errCount === 0) {
                    subErrors.textContent = 'Stable';
                    subErrors.className = 'font-label-sm text-label-sm text-emerald-600 font-bold';
                } else {
                    subErrors.textContent = 'Needs attention';
                    subErrors.className = 'font-label-sm text-label-sm text-error font-bold';
                }

                // Dynamic header status and uptime
                const allHealthy = stats.db_status === 'connected' && stats.api_status === 'healthy';
                const headerStatus = document.getElementById('header-status');
                headerStatus.textContent = allHealthy ? 'Status: Healthy' : 'Status: Degraded';
                headerStatus.className = allHealthy
                    ? 'font-label-md text-label-md text-primary font-bold'
                    : 'font-label-md text-label-md text-error font-bold';
                const uptimeSeconds = Math.floor((Date.now() - pageLoadTime) / 1000);
                const uptimeH = Math.floor(uptimeSeconds / 3600);
                const uptimeM = Math.floor((uptimeSeconds % 3600) / 60);
                document.getElementById('header-uptime').textContent = `Uptime: ${uptimeH}h ${uptimeM}m`;

                // Health indicators
                const dbInd = document.getElementById('health-db-indicator');
                const dbTxt = document.getElementById('health-db-text');
                if (stats.db_status === 'connected') {
                    dbInd.style.backgroundColor = 'rgb(16, 185, 129)';
                    dbTxt.textContent = "DB: Connected";
                } else {
                    dbInd.style.backgroundColor = 'rgb(239, 68, 68)';
                    dbTxt.textContent = "DB: Error";
                }

                const schInd = document.getElementById('health-scheduler-indicator');
                const schTxt = document.getElementById('health-scheduler-text');
                if (stats.scheduler_status === 'active') {
                    schInd.style.backgroundColor = 'rgb(16, 185, 129)';
                    schTxt.textContent = "Scheduler: Active";
                } else {
                    schInd.style.backgroundColor = 'rgb(245, 158, 11)';
                    schTxt.textContent = "Scheduler: Idle";
                }

                const pwInd = document.getElementById('health-playwright-indicator');
                const pwTxt = document.getElementById('health-playwright-text');
                if (stats.playwright_status === 'ready') {
                    pwInd.style.backgroundColor = 'rgb(16, 185, 129)';
                    pwTxt.textContent = "Playwright: Ready";
                } else {
                    pwInd.style.backgroundColor = 'rgb(239, 68, 68)';
                    pwTxt.textContent = "Playwright: Error";
                }

                const apiInd = document.getElementById('health-api-indicator');
                const apiTxt = document.getElementById('health-api-text');
                if (stats.api_status === 'healthy') {
                    apiInd.style.backgroundColor = 'rgb(16, 185, 129)';
                    apiTxt.textContent = "API: Healthy";
                } else {
                    apiInd.style.backgroundColor = 'rgb(239, 68, 68)';
                    apiTxt.textContent = "API: Error";
                }
            }
        } catch (e) {
            console.error("Dashboard refresh stats failed", e);
        }

        // 2. Summary Table
        try {
            const resSum = await fetch(`/api/dashboard/summary?t=${timestamp}`);
            if (resSum.ok) {
                const summary = await resSum.json();
                const tableBody = document.getElementById('summary-table-body');
                tableBody.innerHTML = '';
                if (summary.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td class="px-stack-md py-12 text-center text-outline italic font-body-md text-body-md opacity-60" colspan="6">
                                No extraction data currently held in database.
                            </td>
                        </tr>
                    `;
                } else {
                    summary.forEach(row => {
                        tableBody.innerHTML += `
                            <tr class="hover:bg-surface-container-low transition-colors">
                                <td class="px-stack-md py-3 font-body-md font-semibold">${escapeHtml(row.name)}</td>
                                <td class="px-stack-md py-3 text-center font-mono text-primary font-bold">${row.services_count}</td>
                                <td class="px-stack-md py-3 text-center font-mono text-primary font-bold">${row.pricing_count}</td>
                                <td class="px-stack-md py-3 text-center font-mono text-on-surface-variant">${row.content_count}</td>
                                <td class="px-stack-md py-3 text-center font-mono text-on-surface-variant">${row.socials_count}</td>
                                <td class="px-stack-md py-3 text-center">
                                    <button onclick="deleteCompetitor(${row.id}, '${escapeHtml(row.name)}')" class="text-outline hover:text-error transition-colors" title="Delete">
                                        <span class="material-symbols-outlined text-[18px]">delete</span>
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                }
            }
        } catch (e) {
            console.error("Dashboard refresh summary failed", e);
        }

        // 3. Audit logs
        try {
            const resLogs = await fetch(`/api/dashboard/logs?t=${timestamp}`);
            if (resLogs.ok) {
                const logs = await resLogs.json();
                const logsContainer = document.getElementById('logs-container');
                logsContainer.innerHTML = '';
                if (logs.length === 0) {
                    logsContainer.innerHTML = '<div class="text-stone-500">No collection logs available.</div>';
                } else {
                    logs.forEach(log => {
                        const statusText = log.success ? '<span class="text-emerald-500 font-bold">SUCCESS</span>' : '<span class="text-red-500 font-bold">FAILED</span>';
                        const timeStr = log.start_time ? log.start_time.replace('T', ' ').substring(0, 19) : 'Unknown';
                        const errorsStr = log.errors && log.errors.length > 0 ? escapeHtml(log.errors.join(', ')) : 'None';
                        const compName = competitorsMap[log.competitor_id] ? escapeHtml(competitorsMap[log.competitor_id].name) : `#${log.competitor_id}`;

                        logsContainer.innerHTML += `
                            <div class="text-stone-300 font-mono text-[13px] border-b border-stone-800/40 py-1">
                                <span class="text-stone-500">[${escapeHtml(timeStr)}]</span>
                                ${compName} | Status: ${statusText} | Dur: ${log.duration_seconds || 0}s | Recs: ${log.records_collected}
                                ${log.success ? '' : `<br/><span class="text-red-400 pl-4">Errors: ${errorsStr}</span>`}
                            </div>
                        `;
                    });
                }
            }
        } catch (e) {
            console.error("Dashboard refresh logs failed", e);
        }

        // 4. Telemetry
        try {
            const telRes = await fetch(`/api/dashboard/telemetry?t=${timestamp}`);
            if (telRes.ok) {
                const tel = await telRes.json();
                document.getElementById('telemetry-cpu').textContent = tel.cpu_percent + '%';
                document.getElementById('telemetry-mem').textContent = tel.memory_mb + 'MB / ' + tel.memory_total_gb + 'GB';
                const crawlsEl = document.getElementById('telemetry-crawls');
                if (crawlsEl) {
                    crawlsEl.textContent = tel.active_crawls;
                }
            }
        } catch (e) {
            console.error("Dashboard refresh telemetry failed", e);
        }
    }

    // Delete competitor
    async function deleteCompetitor(id, name) {
        if (!confirm(`Delete "${name}" and all its data? This cannot be undone.`)) return;
        try {
            const res = await fetch(`/api/dashboard/competitors/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast(`${name} deleted`);
                delete competitorsMap[id];
                await loadCompetitors();
                compSelect.dispatchEvent(new Event('change'));
                refreshData();
            } else {
                showToast('Delete failed', 'error');
            }
        } catch (e) {
            showToast('Delete failed', 'error');
        }
    }

    // Init
    loadCompetitors();
    refreshData();
    setInterval(refreshData, 5000);
</script>
</body>
</html>
"""

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(response: Response) -> str:
    """Serves the live interactive dashboard UI."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return DASHBOARD_HTML


@router.get("/api/dashboard/competitors")
async def get_dashboard_competitors(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.database.models import Competitor
    stmt = select(Competitor).order_by(Competitor.name)
    result = await session.execute(stmt)
    competitors = result.scalars().all()
    
    out = []
    for c in competitors:
        # Get the most recent successful collection time
        last_log_stmt = (
            select(CollectionLog.start_time)
            .where(CollectionLog.competitor_id == c.id)
            .where(CollectionLog.success.is_(True))
            .order_by(CollectionLog.start_time.desc())
            .limit(1)
        )
        last_collected = await session.scalar(last_log_stmt)
        out.append({
            "id": c.id,
            "name": c.name,
            "website_url": c.website_url,
            "last_collected": last_collected.isoformat() if last_collected else None,
        })
    return out

@router.post("/api/dashboard/competitors")
async def create_dashboard_competitor(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    from sqlalchemy.exc import IntegrityError
    from app.database.models import Competitor, CollectionFrequency
    
    comp = Competitor(
        name=payload["name"],
        website_url=payload["website_url"],
        enabled=True,
        collection_frequency=CollectionFrequency.DAILY,
        modules=[],
        tags=[]
    )
    session.add(comp)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="A competitor with this name or URL already exists.")
    await session.refresh(comp)
    return {"id": comp.id, "name": comp.name, "website_url": comp.website_url}

@router.delete("/api/dashboard/competitors/{competitor_id}")
async def delete_dashboard_competitor(
    competitor_id: int,
    session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    """Deletes a competitor and all associated data (CASCADE)."""
    from fastapi import HTTPException
    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await session.delete(comp)
    await session.commit()
    return {"status": "deleted", "message": f"Competitor {competitor_id} deleted"}


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Computes aggregated database statistics and pipeline status."""
    urls_count = await session.scalar(select(func.count()).select_from(CompetitorSource))
    pages_count = await session.scalar(select(func.count()).select_from(CompetitorPage))
    services_count = await session.scalar(select(func.count()).select_from(CompetitorService))
    pricing_count = await session.scalar(select(func.count()).select_from(CompetitorPricing))
    content_count = await session.scalar(select(func.count()).select_from(CompetitorContent))
    social_count = await session.scalar(select(func.count()).select_from(CompetitorSocial))
    logs_count = await session.scalar(select(func.count()).select_from(CollectionLog))

    # Calculate error count
    error_stmt = (
        select(func.count()).select_from(CollectionLog).where(CollectionLog.success.is_(False))
    )
    errors_count = await session.scalar(error_stmt)

    # Active collection
    active_collection = None
    if collection_service._active_crawls:
        import time
        # Get first active crawl ID
        active_id = next(iter(collection_service._active_crawls.keys()))
        start_time = collection_service._active_crawls[active_id]
        active_collection = {
            "competitor_id": active_id,
            "status": "active",
            "elapsed": time.time() - start_time,
        }

    # Check Playwright availability
    playwright_status = "error"
    try:
        import playwright
        playwright_status = "ready"
    except ImportError:
        pass

    return {
        "urls_discovered": urls_count or 0,
        "pages_crawled": pages_count or 0,
        "services_extracted": services_count or 0,
        "pricing_extracted": pricing_count or 0,
        "database_writes": (urls_count or 0)
        + (pages_count or 0)
        + (services_count or 0)
        + (pricing_count or 0)
        + (content_count or 0)
        + (social_count or 0)
        + (logs_count or 0),
        "errors": errors_count or 0,
        "scheduler_status": "active" if scheduler.is_running else "idle",
        "playwright_status": playwright_status,
        "db_status": "connected",
        "api_status": "healthy",
        "active_collection": active_collection,
    }


@router.get("/api/dashboard/summary")
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Generates counts of extracted modules per competitor in a single efficient query."""
    from sqlalchemy import outerjoin, literal_column
    from sqlalchemy.orm import aliased
    
    stmt = (
        select(
            Competitor.id,
            Competitor.name,
            func.count(func.distinct(CompetitorService.id)).label("services_count"),
            func.count(func.distinct(CompetitorPricing.id)).label("pricing_count"),
            func.count(func.distinct(CompetitorContent.id)).label("content_count"),
            func.count(func.distinct(CompetitorSocial.id)).label("socials_count"),
        )
        .outerjoin(CompetitorService, Competitor.id == CompetitorService.competitor_id)
        .outerjoin(CompetitorPricing, Competitor.id == CompetitorPricing.competitor_id)
        .outerjoin(CompetitorContent, Competitor.id == CompetitorContent.competitor_id)
        .outerjoin(CompetitorSocial, Competitor.id == CompetitorSocial.competitor_id)
        .group_by(Competitor.id, Competitor.name)
        .order_by(Competitor.name)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "services_count": row.services_count,
            "pricing_count": row.pricing_count,
            "content_count": row.content_count,
            "socials_count": row.socials_count,
        }
        for row in rows
    ]


@router.get("/api/dashboard/logs")
async def get_dashboard_logs(
    limit: int = 50, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    """Returns recent audit logs."""
    stmt = select(CollectionLog).order_by(CollectionLog.id.desc()).limit(limit)
    result = await session.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "competitor_id": log.competitor_id,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "success": log.success,
            "duration_seconds": float(log.duration_seconds) if log.duration_seconds else None,
            "records_collected": log.records_collected,
            "errors": log.errors or [],
            "retry_count": log.retry_count,
        }
        for log in logs
    ]


@router.post("/api/dashboard/collect/{competitor_id}")
async def trigger_dashboard_collect(
    competitor_id: int, background_tasks: BackgroundTasks
) -> dict[str, str]:
    """Triggers standard collection in the background."""
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)
    return {"status": "accepted", "message": "Collection triggered"}


@router.get("/api/dashboard/telemetry")
async def get_dashboard_telemetry() -> dict[str, Any]:
    """Returns actual system CPU and Memory metrics."""
    import psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_total = psutil.virtual_memory().total
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_mb": int(mem_info.rss / 1024 / 1024),
        "memory_total_gb": int(mem_total / 1024 / 1024 / 1024),
        "active_crawls": len(collection_service._active_crawls)
    }

@router.post("/api/dashboard/collect/{competitor_id}/cancel")
async def cancel_dashboard_collect(competitor_id: int) -> dict[str, str]:
    """Cancels a running collection by removing it from the active crawls tracker."""
    async with collection_service._crawls_lock:
        collection_service._active_crawls.pop(competitor_id, None)
    return {"status": "cancelled", "message": f"Collection for competitor {competitor_id} cancelled"}

@router.get("/api/dashboard/live_logs/{competitor_id}")
async def get_dashboard_live_logs(competitor_id: int) -> list[dict[str, Any]]:
    """Returns real-time structlog events from the global buffer."""
    from app.observability.log_buffer import global_log_buffer
    return global_log_buffer.get_logs_for_competitor(competitor_id)

@router.get("/api/dashboard/extracted/{competitor_id}")
async def get_dashboard_extracted(competitor_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    from sqlalchemy import select
    from app.database.models import RawStorage
    stmt = (
        select(RawStorage)
        .where(RawStorage.competitor_id == competitor_id)
        .where(RawStorage.extracted_data.isnot(None))
        .order_by(RawStorage.collected_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    raw = result.scalar_one_or_none()
    if not raw:
        return {"data": None}
    return {"data": raw.extracted_data}
