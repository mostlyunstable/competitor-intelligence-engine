import re

with open("app/static/dashboard.html", "r") as f:
    html = f.read()

modal_html = """
    <!-- Competitor Management Modal -->
    <dialog id="competitor-modal" class="bg-transparent p-0 m-auto backdrop:bg-black/60 backdrop:backdrop-blur-sm z-[100] w-full max-w-2xl hidden">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-2xl flex flex-col w-full text-on-surface">
            <div class="flex justify-between items-center p-stack-md border-b border-outline-variant">
                <h2 class="font-h3 text-h3 text-on-surface flex items-center gap-2" id="comp-modal-title">
                    <span class="material-symbols-outlined text-primary">domain</span>
                    Add Competitor
                </h2>
                <button type="button" onclick="document.getElementById('competitor-modal').close(); document.getElementById('competitor-modal').classList.add('hidden');" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-container transition-colors">
                    <span class="material-symbols-outlined text-outline">close</span>
                </button>
            </div>
            <form id="competitor-form" class="p-stack-md flex flex-col gap-stack-md">
                <input type="hidden" id="comp-id">
                <div class="grid grid-cols-2 gap-gutter">
                    <div class="flex flex-col gap-1">
                        <label class="font-label-sm text-outline">Name</label>
                        <input type="text" id="comp-name" required class="bg-surface-container border border-outline-variant rounded-lg p-2 text-on-surface focus:outline-none focus:border-primary">
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="font-label-sm text-outline">Website URL</label>
                        <input type="url" id="comp-url" required class="bg-surface-container border border-outline-variant rounded-lg p-2 text-on-surface focus:outline-none focus:border-primary">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-gutter">
                    <div class="flex flex-col gap-1">
                        <label class="font-label-sm text-outline">Collection Frequency</label>
                        <select id="comp-frequency" class="bg-surface-container border border-outline-variant rounded-lg p-2 text-on-surface focus:outline-none focus:border-primary">
                            <option value="hourly">Hourly</option>
                            <option value="daily" selected>Daily</option>
                            <option value="weekly">Weekly</option>
                        </select>
                    </div>
                    <div class="flex items-center gap-2 mt-6">
                        <input type="checkbox" id="comp-enabled" checked class="w-4 h-4 text-primary bg-surface-container border-outline-variant rounded focus:ring-primary focus:ring-2">
                        <label class="font-label-md">Enable Monitoring</label>
                    </div>
                </div>
                <div class="flex flex-col gap-1">
                    <label class="font-label-sm text-outline">Modules (Hold Ctrl/Cmd to select multiple)</label>
                    <select id="comp-modules" multiple class="bg-surface-container border border-outline-variant rounded-lg p-2 text-on-surface focus:outline-none focus:border-primary h-24">
                        <option value="discovery" selected>Discovery</option>
                        <option value="company" selected>Company Info</option>
                        <option value="services" selected>Services</option>
                        <option value="pricing" selected>Pricing</option>
                        <option value="content" selected>Content/Blog</option>
                        <option value="social" selected>Social</option>
                    </select>
                </div>
                <div class="flex justify-end gap-2 pt-4 border-t border-outline-variant">
                    <button type="button" id="comp-delete-btn" class="hidden px-4 py-2 bg-error/10 text-error rounded-lg hover:bg-error hover:text-white transition-colors">Delete</button>
                    <div class="flex-1"></div>
                    <button type="button" onclick="document.getElementById('competitor-modal').close(); document.getElementById('competitor-modal').classList.add('hidden');" class="px-4 py-2 border border-outline-variant text-on-surface rounded-lg hover:bg-surface-container transition-colors">Cancel</button>
                    <button type="submit" class="px-6 py-2 bg-primary text-white rounded-lg hover:brightness-105 transition-colors shadow-soft">Save</button>
                </div>
            </form>
        </div>
    </dialog>
"""

# Insert right before the JSON Modal
html = html.replace('        <!-- JSON Modal -->', modal_html + '\n        <!-- JSON Modal -->')

# Change the "Add New Competitor" controls to a "Manage Competitors" button
old_controls = """<label class="block font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">Add New Competitor</label>
                    <input type="text" id="new-comp-name" placeholder="Name (e.g. Acme Corp)" class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-2 text-on-surface focus:outline-none focus:border-primary min-w-0">
                    <input type="text" id="new-comp-url" placeholder="URL (e.g. https://acme.com)" class="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-2 text-on-surface focus:outline-none focus:border-primary min-w-0">
                    <button id="add-comp-btn" class="w-full py-2.5 px-6 bg-surface-container-high text-on-surface font-label-md text-label-md rounded-lg hover:bg-primary hover:text-white transition-all flex items-center justify-center gap-2 border border-outline-variant mt-2">
                        <span class="material-symbols-outlined text-[18px]">add</span>
                        Add
                    </button>"""

new_controls = """<div class="flex justify-between items-center mb-2">
                        <label class="block font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">Competitor Profile</label>
                        <button id="manage-comps-btn" onclick="openCompetitorModal()" class="text-primary hover:underline font-label-sm flex items-center gap-1">
                            <span class="material-symbols-outlined text-[16px]">edit</span> Edit
                        </button>
                    </div>
                    <button onclick="openCompetitorModal(true)" class="w-full py-2 px-4 bg-surface-container text-on-surface font-label-md rounded-lg hover:bg-surface-container-high transition-all flex items-center justify-center gap-2 border border-outline-variant border-dashed">
                        <span class="material-symbols-outlined text-[18px]">add</span> Add New Competitor
                    </button>"""

html = html.replace(old_controls, new_controls)

with open("app/static/dashboard.html", "w") as f:
    f.write(html)

print("Done")
