// dataset.page 会读取 HTML 中 data-page 属性的值。
const page = document.body.dataset.page;
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function toast(message, ok = true) {
    const node = $("#toast");
    if (!node) return;
    node.textContent = message;
    node.style.background = ok ? "var(--leaf-dark)" : "var(--danger)";
    node.hidden = false;
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => node.hidden = true, 2600);
}

// api() 是一个封装了 fetch() 的函数，用于向后端发送 HTTP 请求并处理响应。它接受两个参数：URL 和 options。其中 URL 是请求的地址，options 是一个可选的配置对象，可以包含请求方法、请求体等信息。
async function api(url, options = {}) {
    // fetch() 会向当前域名发起一个 POST 请求，URL 为 ...。这是标准的 HTTP 请求，浏览器会把它发送到 Flask 后端服务器。
    const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    // 返回 JSON: {"ok": True, "user": {...}}
    const data = await res.json();
    if (!data.ok) throw new Error(data.message || "操作失败");
    return data;
}

function formJson(form) {
    return Object.fromEntries(new FormData(form).entries());
}

function updateUser(user) {
    if (!user) return;
    const coin = $("#coinCount");
    const name = $("#userName");
    const role = $("#roleBadge");
    if (coin) coin.textContent = user.coins;
    if (name) name.textContent = user.username;
    if (role) role.textContent = user.role_label;
}

function setActiveNav() {
    $$("[data-nav]").forEach(a => a.classList.toggle("active", a.dataset.nav === page));
}

function seedImage(seed) {
    if (!seed.image_url) return `<div class="seed-placeholder">${seed.name.slice(0, 1)}</div>`;
    return `<img class="seed-img" src="${escapeHtml(seed.image_url)}" alt="${escapeHtml(seed.name)}" onerror="this.outerHTML='<div class=&quot;seed-placeholder&quot;>${escapeHtml(seed.name.slice(0, 1))}</div>'">`;
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#039;",
    }[char]));
}

function formatGold(value) {
    const num = Number(value || 0);
    return Number.isInteger(num) ? String(num) : num.toFixed(2);
}

// 生成种子卡片的 HTML 字符串，根据 mode 参数决定操作按钮区域的内容
// mode 取值："shop"(商店) / "inventory"(仓库) / "admin"(管理) / "plan"(规划)
function seedCard(seed, mode = "shop") {
    // 检查该种子是否已被用户选中（商店页多选功能）
    const selected = window.__selectedSeeds?.has(seed.product_id);
    // 如果已选中，读取已选数量；否则默认为 1
    const selectedQuantity = selected ? window.__selectedSeeds.get(seed.product_id).quantity : 1;
    // 如果种子已下架，显示"已下架"标签；上架则不显示
    const unavailable = seed.is_available ? "" : `<span class="pill">已下架</span>`;
    // 根据收获类型生成不同的成熟天数描述
    const harvest = seed.harvest_type === "multiple"
        ? `首次 ${seed.growth_time_single} 天 / 后续 ${seed.growth_time_multiple} 天`
        : `${seed.growth_time_single} 天成熟`;
    // 根据 mode 生成不同的操作按钮区域
    let action = "";
    if (mode === "shop") {
        // 商店模式：数量输入框 + 选择按钮（支持多选批量购买）+ 购买按钮
        action = `<div class="actions shop-actions">
      <input class="shop-qty" type="number" min="1" value="${selectedQuantity}" aria-label="购买数量">
      <button class="${selected ? "primary" : "ghost"}" data-select="${seed.product_id}">${selected ? "已选" : "选择"}</button>
      <button class="primary" data-buy="${seed.product_id}">购买</button>
    </div>`;
    } else if (mode === "inventory") {
        // 仓库模式：数量输入框（上限为库存量）+ 出售按钮
        action = `<div class="actions">
      <input type="number" min="1" max="${seed.quantity}" value="1" aria-label="出售数量">
      <button class="primary" data-sell="${seed.product_id}">出售</button>
    </div>`;
    } else if (mode === "admin") {
        // 管理模式：编辑 + 上架/下架切换 + 删除按钮
        action = `<div class="actions">
      <button class="ghost" data-edit="${seed.product_id}">编辑</button>
      <button class="ghost" data-toggle="${seed.product_id}">${seed.is_available ? "下架" : "上架"}</button>
      <button class="danger" data-delete="${seed.product_id}">删除</button>
    </div>`;
    } else if (mode === "plan") {
        // 规划模式：显示推荐数量和预计利润
        action = `<div class="price-row"><span>数量 ${seed.quantity}</span><span>利润 +${seed.total_profit}g</span></div>`;
    }
    // 仓库模式下额外显示库存数量标签
    const stock = mode === "inventory" ? `<span class="pill">库存 ${seed.quantity}</span>` : "";
    // 组装完整的卡片 HTML：头部（图片+名称+标签）+ 描述 + 价格信息 + 操作按钮
    return `<article class="card" data-product-id="${seed.product_id}">
    <div class="card-head">
      ${seedImage(seed)}
      <div>
        <h3>${escapeHtml(seed.name)}</h3>
        <div class="meta">
          <span class="pill">${escapeHtml(seed.selling_season)}</span>
          <span class="pill">${escapeHtml(harvest)}</span>
          ${stock}${unavailable}
        </div>
      </div>
    </div>
    <p class="desc">${escapeHtml(seed.description || `${seed.mature_crop_name}最高售价 ${seed.mature_crop_price}g`)}</p>
    <div class="price-row">
      <span>买 ${seed.seed_buy_price}g</span>
      <span>种子卖 ${seed.seed_sell_price}g</span>
    </div>
    <div class="price-row">
      <span>${escapeHtml(seed.mature_crop_name || "作物")}</span>
      <span>最高 ${seed.mature_crop_price}g</span>
    </div>
    ${action}
  </article>`;
}

function groupBySeason(seeds) {
    return seeds.reduce((groups, seed) => {
        const key = seed.selling_season || "全年";
        groups[key] = groups[key] || [];
        groups[key].push(seed);
        return groups;
    }, {});
}

// 加载商店数据并渲染页面
async function loadShop() {
    // 使用 URLSearchParams 对象，将页面上的季节筛选器（#seasonFilter）和搜索输入框（#searchInput）的值转化为 URL 查询字符串格式
    const params = new URLSearchParams({ season: $("#seasonFilter").value, q: $("#searchInput").value });

    // 向 /api/seeds 接口发送带有上述参数的 GET 请求，并等待后端返回数据。
    const data = await api(`/api/seeds?${params}`);

    // 1.将返回的数据存储在全局变量中，以便其他函数使用。
    window.__shopSeeds = data.seeds;
    window.__shopSeedMap = new Map(data.seeds.map(seed => [seed.product_id, seed])); // 以 product_id 为键的映射表，可以 O(1) 快速查找某个种子

    // 2.根据种子的销售季节（selling_season）将种子分组，生成一个以季节为键、种子列表为值的对象。
    const groups = groupBySeason(data.seeds);

    // 3.将分组后的种子数据渲染成 HTML 卡片，并插入到页面上的 #seedGroups 元素中。
    const html = Object.entries(groups).map(([season, seeds]) => `
    <section>
      <h2 class="season-title">${escapeHtml(season)}</h2>
      <div class="seed-grid">${seeds.map(seed => seedCard(seed, "shop")).join("")}</div>
    </section>`).join("");

    // 4.渲染到页面，如果 html 非空 → 将生成的 HTML 插入到页面中 id="seedGroups" 的容器
    $("#seedGroups").innerHTML = html || `<div class="empty">没有找到符合条件的种子。</div>`;

    // 5.更新底部选择栏
    renderSelectionBar();
}

async function loadInventory() {
    const params = new URLSearchParams({ season: $("#seasonFilter").value, q: $("#searchInput").value });
    const data = await api(`/api/inventory?${params}`);
    $("#inventoryGrid").innerHTML = data.items.map(seed => seedCard(seed, "inventory")).join("") || `<div class="empty">仓库里还没有种子。</div>`;
}

// 管理员页面的加载函数，功能类似于 loadShop()，但它调用的是 /api/seeds 接口来获取所有种子数据（包括库存信息），并以 "admin" 模式渲染种子卡片，显示编辑、上下架和删除按钮。
async function loadAdmin() {
    const params = new URLSearchParams({ season: $("#seasonFilter").value, q: $("#searchInput").value });
    const data = await api(`/api/seeds?${params}`);
    window.__seeds = data.seeds;
    
    // 以 "admin" 模式渲染种子卡片，显示编辑、上下架和删除按钮，并插入到页面上的 #adminGrid 元素中。
    $("#adminGrid").innerHTML = data.seeds.map(seed => seedCard(seed, "admin")).join("") || `<div class="empty">没有商品。</div>`;
}

function renderBillSummary(logs) {
    const totals = logs.reduce((acc, log) => {
        const amount = Number(log.total || 0);
        acc.count += 1;
        if (log.action === "buy") acc.buy += amount;
        if (log.action === "sell") acc.sell += amount;
        return acc;
    }, { count: 0, buy: 0, sell: 0 });
    $("#billSummary").innerHTML = `
    <div class="metric"><span>总笔数</span><strong>${totals.count}</strong></div>
    <div class="metric"><span>购买总额</span><strong>${formatGold(totals.buy)}g</strong></div>
    <div class="metric"><span>出售总额</span><strong>${formatGold(totals.sell)}g</strong></div>`;
}

function billRow(log) {
    const actionLabel = log.action === "buy" ? "购买" : "出售";
    return `
    <tr>
      <td>${escapeHtml(log.created_at)}</td>
      <td><span class="bill-action ${log.action}">${actionLabel}</span></td>
      <td>${escapeHtml(log.seed_name)}</td>
      <td class="bill-num">${log.quantity}</td>
      <td class="bill-num">${formatGold(log.unit_price)}g</td>
      <td class="bill-num">${formatGold(log.total)}g</td>
      <td class="bill-user-col">${escapeHtml(log.username)}</td>
    </tr>`;
}

async function loadBills() {
    const params = new URLSearchParams();
    const action = $("#billActionFilter")?.value || "";
    const q = $("#billSearchInput")?.value || "";
    if (action) params.set("action", action);
    if (q) params.set("q", q);
    const data = await api(`/api/logs?${params}`);
    const logs = data.logs || [];
    const table = $("#billTable");
    const body = $("#billTableBody");
    const empty = $("#billEmpty");
    table.classList.toggle("is-owner", data.is_owner);
    if (!logs.length) {
        empty.hidden = false;
        body.innerHTML = "";
        $("#billSummary").innerHTML = "";
        return;
    }
    empty.hidden = true;
    body.innerHTML = logs.map(billRow).join("");
    renderBillSummary(logs);
}

function bindBills() {
    const action = $("#billActionFilter");
    const search = $("#billSearchInput");
    if (action) action.addEventListener("change", loadBills);
    if (search) search.addEventListener("input", () => {
        clearTimeout(window.__billSearchTimer);
        window.__billSearchTimer = setTimeout(loadBills, 180);
    });
}

function bindFilters(loader) {
    const season = $("#seasonFilter");
    const search = $("#searchInput");
    if (season) season.addEventListener("change", loader);
    if (search) search.addEventListener("input", () => {
        clearTimeout(window.__searchTimer);
        window.__searchTimer = setTimeout(loader, 180);
    });
}

function bindAuth() {
    // 切换登录/注册标签页
    // 遍历所有带有 data-auth-tab 属性的按钮，绑定点击事件。
    $$("[data-auth-tab]").forEach(btn => btn.addEventListener("click", () => {
        // 点击时，遍历所有标签，只有当前被点击的按钮才会被添加 active 类（tab === btn 为真时激活）。
        $$("[data-auth-tab]").forEach(tab => tab.classList.toggle("active", tab === btn));
        // 根据被点击按钮的 data-auth-tab 属性值（"login" 或 "register"），控制登录表单和注册表单的 hidden 属性，实现显示/隐藏。
        $("#loginForm").hidden = btn.dataset.authTab !== "login";
        $("#registerForm").hidden = btn.dataset.authTab !== "register";
    }));

    // 绑定登录表单提交事件
    // 1. 给 id="loginForm" 的表单添加"提交"事件监听器。当用户点击登录按钮时，这个函数会被触发。
    $("#loginForm").addEventListener("submit", async event => {
        // 2. 阻止表单的默认提交行为（默认行为会刷新页面）
        event.preventDefault();
        try {
            // - await 等待服务器响应
            // - event.currentTarget 就是那个登录表单
            // - formJson() 把表单里所有输入框的值转成 JSON 对象，比如 {"username":"xxx","password":"xxx"}
            // - JSON.stringify() 再把对象转成 JSON 字符串，准备发送给服务器
            // - api() 是一个自定义的封装函数，向服务器的 /api/login 发送 POST 请求
            await api("/api/login", { method: "POST", body: JSON.stringify(formJson(event.currentTarget)) });

            // 3. 登录成功后，跳转到 /shop 页面
            location.href = "/shop";
        } catch (error) {
            toast(error.message, false);
        }
    });

    // 绑定注册表单提交事件
    $("#registerForm").addEventListener("submit", async event => {
        event.preventDefault();
        try {
            // 向服务器的 /api/register 发送 POST（提交） 请求，携带注册表单的数据
            // body: 指定了 HTTP 请求的“请求体”（Payload），即需要发送给服务器的实际数据内容。
            // SON.stringify() 将数据转换为 JSON 格式的字符串。
            const data = await api("/api/register", { method: "POST", body: JSON.stringify(formJson(event.currentTarget)) });
            // 返回的 data 是一个 JS 对象，比如 { ok: true, message: "注册成功，可以登录了。" }
            // 注册成功，弹出提示消息，显示 data.message 即 "注册成功，可以登录了。"
            toast(data.message);
            // 然后切换到登录标签页，显示登录表单   
            $$("[data-auth-tab]")[0].click();
        } catch (error) {
            toast(error.message, false);
        }
    });
}

function bindGlobal() {
    const logout = $("#logoutBtn");
    if (logout) {
        logout.addEventListener("click", async () => {
            await api("/api/logout", { method: "POST", body: "{}" });
            location.href = "/auth";
        });
    }

    // 金币点击编辑功能
    const coinCount = $("#coinCount");
    if (coinCount) {
        coinCount.addEventListener("click", async () => {
            const currentCoins = parseInt(coinCount.textContent) || 0;
            const newCoins = prompt("请输入新的金币数量：", currentCoins);

            if (newCoins === null) return; // 用户取消

            const coinsNum = parseInt(newCoins);
            if (isNaN(coinsNum) || coinsNum < 0) {
                toast("请输入有效的正整数", false);
                return;
            }

            try {
                const data = await api("/api/update-coins", {
                    method: "POST",
                    body: JSON.stringify({ user_id: window.__currentUserId, coins: coinsNum })
                });
                updateUser(data.user);
                toast("金币更新成功");
            } catch (error) {
                toast(error.message, false);
            }
        });
    }
}

function bindShopActions() {
    window.__selectedSeeds = window.__selectedSeeds || new Map();
    ensureSelectionBar();
    $("#seedGroups").addEventListener("click", async event => {
        // 先检查是不是「选择」按钮被点击了，如果是，就调用 toggleSelection() 来切换选择状态，并返回（不继续执行后面的购买逻辑）。
        const selectBtn = event.target.closest("[data-select]");
        if (selectBtn) {
            toggleSelection(selectBtn);
            return;
        }

        // 再检查是不是「购买」按钮
        const btn = event.target.closest("[data-buy]");
        if (!btn) return;

        // 如果是购买按钮被点击了，找到对应的种子卡片，读取用户输入的购买数量，然后向后端发送购买请求。
        const card = btn.closest(".card"); // 找到按钮所在的卡片
        const quantity = $(".shop-qty", card).value; // 从卡片中的数量输入框读取值
        try {
            const data = await api("/api/buy", { // 发送购买请求
                method: "POST", 
                body: JSON.stringify({ 
                    product_id: btn.dataset.buy, // 按钮的 data-buy 属性值 = 商品ID
                    quantity // 输入框的值 = 购买数量
                })
            });
            updateUser(data.user); // 用后端返回的最新用户信息更新页面金币
            toast(data.message);
        } catch (error) {
            toast(error.message, false);
        }
    });
    $("#seedGroups").addEventListener("input", event => {
        const input = event.target.closest(".shop-qty");
        if (!input) return;
        const card = input.closest(".card");
        const productId = Number(card.dataset.productId);
        if (!window.__selectedSeeds.has(productId)) return;
        const quantity = Math.max(1, Number(input.value || 1));
        const seed = window.__selectedSeeds.get(productId).seed;
        window.__selectedSeeds.set(productId, { seed, quantity });
        renderSelectionBar();
    });
    $("#clearSelection")?.addEventListener("click", () => {
        window.__selectedSeeds.clear();
        refreshSelectionButtons();
        renderSelectionBar();
    });
    $("#buySelection")?.addEventListener("click", buySelectedSeeds);
}

function ensureSelectionBar() {
    if ($("#shopSelectionBar")) return;
    document.body.insertAdjacentHTML("beforeend", `
    <section id="shopSelectionBar" class="selection-bar" hidden>
      <div>
        <strong id="selectionSummary">未选择种子</strong>
        <div id="selectionList" class="selection-list"></div>
      </div>
      <div class="selection-total">
        <div class="selection-total-label">总费用</div>
        <div class="selection-total-price">
          <span id="selectionTotal">0</span><span class="selection-price-unit">g</span>
        </div>
      </div>
      <div class="selection-actions">
        <button class="ghost" id="clearSelection" type="button">清空</button>
        <button class="primary" id="buySelection" type="button">购买选中</button>
      </div>
    </section>
  `);
}

function toggleSelection(button) {
    const productId = Number(button.dataset.select); // 从 data-select 属性拿到商品ID
    const card = button.closest(".card"); 
    const seed = window.__shopSeedMap.get(productId); // 从全局Map中O(1)查找种子数据

    if (!seed) return;

    if (window.__selectedSeeds.has(productId)) {
        // ── 已经选中了 → 取消选中 ──
        window.__selectedSeeds.delete(productId);
        button.textContent = "选择";
        button.classList.remove("primary");
        button.classList.add("ghost");
    } else {
        // ── 还没选中 → 添加选中 ──
        const quantity = Math.max(1, Number($(".shop-qty", card).value || 1));
        window.__selectedSeeds.set(productId, { seed, quantity });
        button.textContent = "已选";
        button.classList.remove("ghost");
        button.classList.add("primary");
    }
    renderSelectionBar(); // 更新底部选择栏
}

function selectedItems() {
    return Array.from((window.__selectedSeeds || new Map()).values());
}

function selectionTotal(items = selectedItems()) {
    return items.reduce((total, item) => total + item.seed.seed_buy_price * item.quantity, 0);
}

function renderSelectionBar() {
    const bar = $("#shopSelectionBar");
    if (!bar) return;
    const items = selectedItems();
    bar.hidden = items.length === 0;
    document.body.classList.toggle("has-selection", items.length > 0);
    if (!items.length) return;
    const quantity = items.reduce((sum, item) => sum + item.quantity, 0);
    $("#selectionSummary").textContent = `已选择 ${items.length} 种，共 ${quantity} 包种子`;
    $("#selectionList").innerHTML = items.map(item => `
    <span class="selection-chip">${escapeHtml(item.seed.name)} x${item.quantity}</span>
  `).join("");
    $("#selectionTotal").textContent = selectionTotal(items).toFixed(0);
}

function refreshSelectionButtons() {
    $$("[data-select]").forEach(button => {
        const selected = window.__selectedSeeds.has(Number(button.dataset.select));
        button.textContent = selected ? "已选" : "选择";
        button.classList.toggle("primary", selected);
        button.classList.toggle("ghost", !selected);
    });
}

async function buySelectedSeeds() {
    const items = selectedItems();
    if (!items.length) {
        toast("请先选择要购买的种子。", false);
        return;
    }

    // ── 前端预检：金币够不够 ──
    const coins = Number($("#coinCount")?.textContent || 0);
    const total = selectionTotal(items);
    if (total > coins) {
        toast("金币不足，无法购买选中种子。", false);
        return;
    }
    try {
        let latestUser = null;
        // 串行购买每一种选中的种子
        for (const item of items) {
            const data = await api("/api/buy", {
                method: "POST",
                body: JSON.stringify({ product_id: item.seed.product_id, quantity: item.quantity }),
            });
            latestUser = data.user;
        }

        // ── 全部购买成功后 ──
        updateUser(latestUser); // 更新用户信息
        window.__selectedSeeds.clear();  // 清空选中列表
        refreshSelectionButtons();  // 刷新按钮状态
        renderSelectionBar();  // 刷新选择栏
        toast("选中种子购买成功。");
    } catch (error) {
        toast(error.message, false);
    }
}

function bindInventoryActions() {
    $("#inventoryGrid").addEventListener("click", async event => {
        const btn = event.target.closest("[data-sell]");
        if (!btn) return;
        const card = btn.closest(".card");
        const quantity = $("input", card).value;
        try {
            const data = await api("/api/sell", { method: "POST", body: JSON.stringify({ product_id: btn.dataset.sell, quantity }) });
            updateUser(data.user);
            await loadInventory();
            toast(data.message);
        } catch (error) {
            toast(error.message, false);
        }
    });
}

function seedFormPayload(form) {
    const data = formJson(form);
    for (const key of ["growth_time_single", "growth_time_multiple", "seed_buy_price", "seed_sell_price", "mature_crop_price", "is_available"]) {
        data[key] = Number(data[key]);
    }
    return data;
}

function resetSeedForm() {
    $("#seedForm").reset();
    $("[name=product_id]").value = "";
}

function fillSeedForm(seed) {
    const form = $("#seedForm");
    Object.entries(seed).forEach(([key, value]) => {
        const input = $(`[name=${key}]`, form);
        if (input) input.value = value ?? "";
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
}

/**
 * 绑定管理页面（皮埃尔商品管理）的所有交互事件
 * 
 * 包含三大功能模块：
 *   1. 表单提交（新增/编辑种子）
 *   2. 清空表单按钮
 *   3. 卡片操作按钮（编辑/上架下架切换/删除）
 * 
 * 对应后端 API：
 *   POST   /api/admin/seeds           → add_seed()     新增种子
 *   PUT    /api/admin/seeds/:id        → edit_seed()    编辑种子
 *   POST   /api/admin/seeds/:id/toggle → toggle_seed()  上架/下架切换
 *   DELETE /api/admin/seeds/:id        → delete_seed()  删除种子
 */
function bindAdminActions() {

    // ─── 1. 表单提交事件：新增或编辑种子 ───
    // 表单是双用途的：隐藏字段 product_id 为空时是新增，有值时是编辑
    $("#seedForm").addEventListener("submit", async event => {
        event.preventDefault();   // 阻止表单默认提交行为（页面刷新）
        const form = event.currentTarget;

        // 读取隐藏字段 product_id 的值，用于判断是新增还是编辑
        const productId = $("[name=product_id]", form).value;

        // seedFormPayload 将表单数据收集为 JSON 对象，并将数值字段从字符串转为数字类型
        const payload = seedFormPayload(form);

        try {
            // 根据 productId 是否存在，决定调用新增 API 还是编辑 API
            // productId 有值 → 编辑：PUT /api/admin/seeds/{productId} → 后端 edit_seed()
            // productId 为空 → 新增：POST /api/admin/seeds → 后端 add_seed()
            const url = productId ? `/api/admin/seeds/${productId}` : "/api/admin/seeds";
            const method = productId ? "PUT" : "POST";

            const data = await api(url, { method, body: JSON.stringify(payload) });

            toast(data.message);          // 显示操作结果提示
            resetSeedForm();              // 清空表单（包括隐藏的 product_id），恢复为新增模式
            await loadAdmin();            // 重新加载商品列表，反映最新数据
        } catch (error) {
            toast(error.message, false);  // 显示错误提示（false 表示错误样式）
        }
    });

    // ─── 2. 清空表单按钮 ───
    // 点击「清空」按钮，将表单恢复为初始状态（新增模式）
    $("#resetSeedForm").addEventListener("click", resetSeedForm);

    // ─── 3. 卡片操作按钮：编辑 / 上架下架切换 / 删除 ───
    // 使用事件委托：在 #adminGrid 容器上统一监听，通过 data-* 属性区分按钮类型
    $("#adminGrid").addEventListener("click", async event => {
        // 通过 closest() 向上查找最近的匹配元素，确定点击的是哪种按钮
        const edit = event.target.closest("[data-edit]");     // 编辑按钮
        const toggle = event.target.closest("[data-toggle]"); // 上架/下架切换按钮
        const del = event.target.closest("[data-delete]");    // 删除按钮

        try {
            // ── 编辑：填充表单 ──
            // 从全局缓存 window.__seeds 中查找该种子的完整数据，填充到表单中
            // 填充后隐藏字段 product_id 会有值，下次提交时自动走编辑（PUT）逻辑
            // 页面会自动滚动到顶部表单位置
            if (edit) {
                const seed = window.__seeds.find(item => item.product_id === Number(edit.dataset.edit));
                fillSeedForm(seed);
            }

            // ── 上架/下架切换 ──
            // 后端逻辑：读取当前 is_available 状态 → 取反 → 写回
            // 刷新列表后按钮文字会自动变化（上架↔下架）
            if (toggle) {
                const data = await api(`/api/admin/seeds/${toggle.dataset.toggle}/toggle`, { method: "POST", body: "{}" });
                toast(data.message);
                await loadAdmin();            // 刷新列表，按钮文字更新
            }

            // ── 删除 ──
            // 先弹出确认框，用户确认后才发送删除请求
            // 后端删除顺序：inventory → logs → crops → seeds（遵循外键约束）
            if (del && confirm("确定删除这个种子商品吗？")) {
                const data = await api(`/api/admin/seeds/${del.dataset.delete}`, { method: "DELETE" });
                toast(data.message);
                await loadAdmin();            // 刷新列表，已删除的卡片消失
            }
        } catch (error) {
            toast(error.message, false);
        }
    });
}

function bindPlanner() {
    $("#plannerForm").addEventListener("submit", async event => {
        event.preventDefault();
        try {
            const data = await api("/api/recommend", { method: "POST", body: JSON.stringify(formJson(event.currentTarget)) });
            const plan = data.plan;
            $("#plannerSummary").innerHTML = `
        <div class="metric"><span>总成本</span><strong>${plan.total_cost}g</strong></div>
        <div class="metric"><span>预计收入</span><strong>${plan.total_revenue}g</strong></div>
        <div class="metric"><span>预计利润</span><strong>${plan.total_profit}g</strong></div>`;
            $("#plannerResult").innerHTML = plan.items.map(seed => seedCard(seed, "plan")).join("") || `<div class="empty">当前条件下没有正收益组合。</div>`;
        } catch (error) {
            toast(error.message, false);
        }
    });
}

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", async () => {
    setActiveNav();
    bindGlobal();
    if (page === "auth") bindAuth();
    if (page === "shop") {
        bindFilters(loadShop); // 绑定筛选条件变化时重新加载商店数据
        bindShopActions(); // 绑定商店页面上的按钮点击事件
        // await 的作用是等待一个异步操作完成，再继续执行后面的代码。
        await loadShop(); // 加载种子数据并渲染页面
    }
    if (page === "warehouse") {
        bindFilters(loadInventory);
        bindInventoryActions();
        await loadInventory();
    }
    if (page === "admin") {
        bindFilters(loadAdmin);
        bindAdminActions();
        await loadAdmin();
    }
    if (page === "billing") {
        bindBills();
        await loadBills();
    }
    if (page === "planner") bindPlanner();
});
