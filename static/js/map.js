(function () {
  "use strict";

  var TASHKENT = [41.38, 69.29];
  var markers = {};
  var searchQuery = "";
  var subjectSlug = new URLSearchParams(window.location.search).get("subject") || "";
  var loadTimer = null;
  var map;
  var meMarker = null;
  var courseId = "";
  var suggestTimer = null;
  var suggestToken = 0;
  var centerSheet;
  var centerSheetPanel;
  var centerSheetTitle;
  var centerSheetBody;
  var centerSheetFooter;
  var centerSheetDrag;
  var centerSheetClose;
  var previousBodyOverflow = "";
  var dragState = null;

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function fullPrice(value) {
    return value == null ? "" : Number(value).toLocaleString("ru-RU");
  }

  function priceText(center) {
    var min = center.price_min != null ? center.price_min : center.price_monthly;
    var max = center.price_max != null ? center.price_max : center.price_monthly;
    if (min != null && max != null) return fullPrice(min) + " - " + fullPrice(max) + " UZS";
    if (min != null) return fullPrice(min) + " UZS";
    return "Narx ko'rsatilmagan";
  }

  function safeHttpUrl(value) {
    if (!value) return "";
    try {
      var url = new URL(value, window.location.origin);
      return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
    } catch (error) {
      return "";
    }
  }

  function coursePrice(course) {
    var min = course.price_min;
    var max = course.price_max;
    if (min != null && max != null) return fullPrice(min) + " - " + fullPrice(max) + " UZS";
    if (min != null) return fullPrice(min) + " UZS";
    if (max != null) return fullPrice(max) + " UZS";
    return "";
  }

  function renderCenterSheet(center) {
    var imageUrl = safeHttpUrl(center.image_url);
    if (!imageUrl && center.images && center.images.length) {
      imageUrl = safeHttpUrl(center.images[0].image);
    }

    var cover = imageUrl
      ? '<img class="center-sheet__cover" src="' + esc(imageUrl) + '" alt="' + esc(center.name) + '">'
      : '<div class="center-sheet__cover center-sheet__placeholder" aria-hidden="true"><span class="material-symbols-outlined">school</span></div>';
    var rating = Number(center.rating) > 0
      ? '<div class="center-sheet__rating">★ ' + esc(Number(center.rating).toFixed(1)) + '</div>'
      : "";
    var subjects = (center.subjects || []).map(function (subject) {
      return subject && subject.name ? '<span class="center-sheet__chip">' + esc(subject.name) + '</span>' : "";
    }).join("");
    var courses = (center.courses || []).map(function (course) {
      if (!course || !course.name) return "";
      var category = course.category && course.category.name ? " · " + esc(course.category.name) : "";
      var price = coursePrice(course);
      return '<div class="center-sheet__course"><span class="center-sheet__course-name">' +
        esc(course.name) + category + '</span>' +
        (price ? '<span class="center-sheet__course-price">' + esc(price) + '</span>' : "") +
        '</div>';
    }).join("");
    var description = center.description
      ? '<p class="center-sheet__description">' + esc(center.description) + '</p>'
      : "";
    var website = safeHttpUrl(center.website);
    var websiteLink = website
      ? '<p class="center-sheet__description"><a href="' + esc(website) + '" target="_blank" rel="noopener noreferrer">Veb-saytni ochish</a></p>'
      : "";
    var phone = String(center.phone || "").trim();
    var phoneHref = phone.replace(/[^\d+]/g, "");

    centerSheetTitle.textContent = center.name || "O'quv markazi";
    centerSheetBody.innerHTML =
      '<div class="center-sheet__overview">' + cover +
        '<div class="min-w-0"><p class="center-sheet__address">' + esc(center.address || "Manzil ko'rsatilmagan") + '</p>' +
          '<p class="center-sheet__address">' + esc(priceText(center)) + '</p>' + rating +
        '</div>' +
      '</div>' +
      description +
      (subjects ? '<h3 class="center-sheet__section-title">Yo\'nalishlar</h3><div class="center-sheet__chips">' + subjects + '</div>' : "") +
      (courses ? '<h3 class="center-sheet__section-title">Kurslar</h3>' + courses : "") +
      websiteLink;

    centerSheetFooter.innerHTML =
      (phoneHref ? '<a class="center-sheet__action center-sheet__action--secondary" href="tel:' + esc(phoneHref) + '">' +
        '<span class="material-symbols-outlined">call</span>Qo\'ng\'iroq</a>' : "") +
      '<a class="center-sheet__action center-sheet__action--primary" href="/about/' +
        encodeURIComponent(center.id) + '/">Batafsil</a>';
  }

  function openCenterSheet(center) {
    var wasOpen = centerSheet.classList.contains("is-open");
    renderCenterSheet(center);
    if (!wasOpen) {
      centerSheetPanel.style.height = "";
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      centerSheet.classList.add("is-open");
      centerSheet.setAttribute("aria-hidden", "false");
      centerSheetDrag.setAttribute("aria-expanded", "true");
    }
    centerSheetClose.focus();
  }

  function closeCenterSheet() {
    if (!centerSheet.classList.contains("is-open")) return;
    centerSheet.classList.remove("is-open");
    centerSheet.setAttribute("aria-hidden", "true");
    centerSheetDrag.setAttribute("aria-expanded", "false");
    document.body.style.overflow = previousBodyOverflow;
  }

  function setupCenterSheet() {
    centerSheet = document.getElementById("center-sheet");
    centerSheetPanel = document.getElementById("center-sheet-panel");
    centerSheetTitle = document.getElementById("center-sheet-title");
    centerSheetBody = document.getElementById("center-sheet-body");
    centerSheetFooter = document.getElementById("center-sheet-footer");
    centerSheetDrag = document.getElementById("center-sheet-drag");
    centerSheetClose = document.getElementById("center-sheet-close");

    document.getElementById("center-sheet-backdrop").addEventListener("click", closeCenterSheet);
    centerSheetClose.addEventListener("click", closeCenterSheet);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeCenterSheet();
    });

    centerSheetDrag.addEventListener("pointerdown", function (event) {
      if (!event.isPrimary || (event.pointerType === "mouse" && event.button !== 0)) return;
      dragState = {
        pointerId: event.pointerId,
        startY: event.clientY,
        startHeight: centerSheetPanel.getBoundingClientRect().height,
        deltaY: 0
      };
      centerSheetPanel.classList.add("is-dragging");
      centerSheetDrag.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    centerSheetDrag.addEventListener("pointermove", function (event) {
      if (!dragState || event.pointerId !== dragState.pointerId) return;
      dragState.deltaY = event.clientY - dragState.startY;
      var minHeight = Math.min(280, window.innerHeight * 0.35);
      var maxHeight = window.innerHeight * 0.86;
      var height = Math.max(minHeight, Math.min(maxHeight, dragState.startHeight - dragState.deltaY));
      centerSheetPanel.style.height = Math.round(height) + "px";
    });
    function finishSheetDrag(event) {
      if (!dragState || event.pointerId !== dragState.pointerId) return;
      var deltaY = dragState.deltaY;
      dragState = null;
      centerSheetPanel.classList.remove("is-dragging");
      if (deltaY > Math.max(120, window.innerHeight * 0.18)) {
        closeCenterSheet();
      } else if (deltaY < -60) {
        centerSheetPanel.style.height = Math.round(window.innerHeight * 0.86) + "px";
      } else {
        centerSheetPanel.style.height = "56dvh";
      }
    }
    centerSheetDrag.addEventListener("pointerup", finishSheetDrag);
    centerSheetDrag.addEventListener("pointercancel", finishSheetDrag);
    centerSheetDrag.addEventListener("keydown", function (event) {
      if (event.key === "ArrowUp") {
        event.preventDefault();
        centerSheetPanel.style.height = Math.round(window.innerHeight * 0.86) + "px";
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        if (centerSheetPanel.getBoundingClientRect().height > window.innerHeight * 0.65) {
          centerSheetPanel.style.height = "56dvh";
        } else {
          closeCenterSheet();
        }
      }
    });
  }

  async function api(path, params) {
    var query = new URLSearchParams(params || {}).toString();
    var response = await fetch("/api/" + path + "/" + (query ? "?" + query : ""));
    if (!response.ok) throw new Error("API " + response.status);
    return response.json();
  }

  function visibleBounds() {
    if (!map) return null;
    var bounds = map.getBounds();
    var sw = bounds[0];
    var ne = bounds[1];
    return {
      south: sw[0].toFixed(7),
      west: sw[1].toFixed(7),
      north: ne[0].toFixed(7),
      east: ne[1].toFixed(7)
    };
  }

  function clearMarkers() {
    Object.keys(markers).forEach(function (id) {
      map.geoObjects.remove(markers[id]);
    });
    markers = {};
  }

  var PinLayout = null;
  var activeRequest = 0;

  function renderMarkers(list) {
    clearMarkers();
    if (!PinLayout) {
      PinLayout = ymaps.templateLayoutFactory.createClass(
        '<div class="edu-pin"><div class="edu-pin__name">{{ properties.name }}</div>' +
        '<div class="edu-pin__price">{{ properties.price }}</div><span class="edu-pin__tail"></span></div>'
      );
    }
    list.forEach(function (center) {
      if (!isFinite(center.latitude) || !isFinite(center.longitude)) return;
      var marker = new ymaps.Placemark(
        [center.latitude, center.longitude],
        { hintContent: center.name, name: center.name, price: priceText(center) },
        {
          iconLayout: PinLayout,
          iconOffset: [-72, -46],
          iconShape: { type: "Rectangle", coordinates: [[0, 0], [144, 46]] },
          cursor: "pointer",
          openBalloonOnClick: false
        }
      );
      function openCenter() { showCenter(center); }
      marker.events.add("click", openCenter);
      marker.events.add("tap", openCenter);
      map.geoObjects.add(marker);
      markers[center.id] = marker;
    });
  }

  // Marker bosilganda: avval ro'yxatdagi ma'lumot, so'ng to'liq ma'lumot (/api/centers/<id>/)
  async function showCenter(center) {
    var token = ++activeRequest;
    openCenterSheet(center);
    try {
      var full = await api("centers/" + encodeURIComponent(center.id), {});
      if (token === activeRequest) renderCenterSheet(full);
    } catch (error) {
      console.error(error);
    }
  }

  async function loadVisibleCenters() {
    var bounds = visibleBounds();
    if (!bounds) return;
    try {
      var params = Object.assign({}, bounds, searchQuery ? { q: searchQuery } : {}, subjectSlug ? { subject: subjectSlug } : {}, courseId ? { course: courseId } : {});
      var list = await api("centers", params);
      renderMarkers(list);
      document.getElementById("count-pill").textContent = list.length + " ta markaz";
      document.getElementById("count-pill").classList.remove("hidden");
    } catch (error) {
      console.error(error);
    }
  }

  // Tanlangan kurs/qidiruv bo'yicha BARCHA mos markazlarni olib, xaritani ularga moslaydi
  async function applyFilter() {
    try {
      var params = Object.assign({}, searchQuery ? { q: searchQuery } : {}, subjectSlug ? { subject: subjectSlug } : {}, courseId ? { course: courseId } : {});
      var list = await api("centers", params);
      renderMarkers(list);
      var pill = document.getElementById("count-pill");
      pill.textContent = list.length + " ta markaz";
      pill.classList.remove("hidden");
      if (!list.length) return;
      if (list.length === 1) {
        map.setCenter([list[0].latitude, list[0].longitude], 15);
      } else {
        var lats = list.map(function (c) { return c.latitude; });
        var lons = list.map(function (c) { return c.longitude; });
        map.setBounds([[Math.min.apply(null, lats), Math.min.apply(null, lons)], [Math.max.apply(null, lats), Math.max.apply(null, lons)]],
          { checkZoomRange: true, zoomMargin: [140, 60, 100, 60] });
      }
    } catch (error) {
      console.error(error);
    }
  }

  function hideSuggest() {
    var box = document.getElementById("suggest");
    box.classList.add("hidden");
    box.innerHTML = "";
  }

  function suggestRow(attrs, icon, title, sub, extra) {
    return '<button type="button" class="suggest-row w-full text-left px-4 py-2.5 flex items-center gap-3 hover:bg-surface-container" ' + attrs + '>' +
      '<span class="material-symbols-outlined text-[20px] text-tertiary">' + icon + '</span>' +
      '<span class="min-w-0 flex-1"><span class="block font-semibold text-on-surface truncate">' + esc(title) + '</span>' +
      '<span class="block text-xs text-on-surface-variant truncate">' + esc(sub) + '</span></span>' +
      (extra ? '<span class="text-xs font-bold text-on-surface">' + esc(extra) + '</span>' : "") + '</button>';
  }

  function renderSuggest(data) {
    var box = document.getElementById("suggest");
    var html = "";
    (data.courses || []).forEach(function (c) {
      html += suggestRow('data-kind="course" data-id="' + esc(c.id) + '" data-name="' + esc(c.name) + '"', "school", c.name, c.center_count + " ta markaz");
    });
    (data.subjects || []).forEach(function (s) {
      html += suggestRow('data-kind="subject" data-slug="' + esc(s.slug) + '" data-name="' + esc(s.name) + '"', "category", s.name, "Yo'nalish · " + s.center_count + " ta markaz");
    });
    (data.centers || []).forEach(function (c) {
      html += suggestRow('data-kind="center" data-id="' + esc(c.id) + '" data-name="' + esc(c.name) + '"', "location_on", c.name, c.address, Number(c.rating) > 0 ? "★ " + Number(c.rating).toFixed(1) : "");
    });
    if (!html) html = '<div class="px-4 py-3 text-sm text-on-surface-variant">Hech narsa topilmadi</div>';
    box.innerHTML = html;
    box.classList.remove("hidden");
  }

  async function fetchSuggest(q) {
    var token = ++suggestToken;
    try {
      var data = await api("suggest", { q: q });
      if (token === suggestToken) renderSuggest(data);
    } catch (error) {
      console.error(error);
    }
  }

  function chooseSuggest(row, input) {
    var kind = row.getAttribute("data-kind");
    var name = row.getAttribute("data-name");
    input.value = name;
    document.getElementById("clear-btn").classList.remove("hidden");
    document.getElementById("clear-btn").classList.add("flex");
    hideSuggest();
    courseId = "";
    subjectSlug = "";
    searchQuery = "";
    if (kind === "course") {
      courseId = row.getAttribute("data-id");
    } else if (kind === "subject") {
      subjectSlug = row.getAttribute("data-slug");
    } else {
      searchQuery = name;
    }
    applyFilter().then(function () {
      if (kind === "center") {
        showCenter({ id: Number(row.getAttribute("data-id")), name: name });
      }
    });
  }

  function scheduleLoad() {
    clearTimeout(loadTimer);
    loadTimer = setTimeout(loadVisibleCenters, 250);
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupCenterSheet();
    ymaps.ready(function () {
      map = new ymaps.Map("map", {
        center: TASHKENT,
        zoom: 11,
        controls: []
      }, { suppressMapOpenBlock: true });

      map.events.add("boundschange", scheduleLoad);

      document.getElementById("locate-btn").addEventListener("click", function () {
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition(function (pos) {
          var coords = [pos.coords.latitude, pos.coords.longitude];
          map.setCenter(coords, 14);
          if (meMarker) map.geoObjects.remove(meMarker);
          meMarker = new ymaps.Placemark(coords, { hintContent: "Siz shu yerdasiz" }, {
            preset: "islands#blueCircleDotIcon"
          });
          map.geoObjects.add(meMarker);
        }, function () {
          alert("Joylashuvga ruxsat berilmadi. Brauzer sozlamalaridan ruxsat bering.");
        }, { enableHighAccuracy: true, timeout: 10000 });
      });

      document.getElementById("zoom-in").addEventListener("click", function () { map.setZoom(map.getZoom() + 1); });
      document.getElementById("zoom-out").addEventListener("click", function () { map.setZoom(map.getZoom() - 1); });

      var form = document.getElementById("search-form");
      var input = document.getElementById("search-input");
      var clearBtn = document.getElementById("clear-btn");
      var suggestBox = document.getElementById("suggest");

      input.addEventListener("input", function () {
        var v = input.value.trim();
        clearBtn.classList.toggle("hidden", !v);
        clearBtn.classList.toggle("flex", !!v);
        clearTimeout(suggestTimer);
        if (!v) { hideSuggest(); return; }
        suggestTimer = setTimeout(function () { fetchSuggest(v); }, 200);
      });
      input.addEventListener("focus", function () {
        if (input.value.trim() && !suggestBox.innerHTML) fetchSuggest(input.value.trim());
      });
      suggestBox.addEventListener("click", function (event) {
        var row = event.target.closest(".suggest-row");
        if (row) chooseSuggest(row, input);
      });
      document.addEventListener("click", function (event) {
        if (!event.target.closest("#search-form") && !event.target.closest("#suggest")) hideSuggest();
      });
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        searchQuery = input.value.trim();
        courseId = "";
        subjectSlug = "";
        hideSuggest();
        applyFilter();
      });
      clearBtn.addEventListener("click", function () {
        input.value = "";
        searchQuery = "";
        courseId = "";
        subjectSlug = "";
        clearBtn.classList.add("hidden");
        clearBtn.classList.remove("flex");
        hideSuggest();
        loadVisibleCenters();
      });

      document.getElementById("nav-map").addEventListener("click", function () {
        loadVisibleCenters();
      });
      document.getElementById("nav-saved").addEventListener("click", function () {
        window.location.href = "/";
      });

      loadVisibleCenters();
    });
  });
})();
