/* Live calculations for the booking form. The server recalculates everything on save;
   this only mirrors voucher/calc.py so the user sees the numbers while typing. */
(function () {
  "use strict";

  var form = document.getElementById("booking-form");
  if (!form) return;

  var COMPANY_STATE = form.getAttribute("data-company-state") || "";
  var GSTIN_RE = /^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
  var DAY = 86400000;

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function out(name, text) {
    $$('[data-out="' + name + '"]').forEach(function (el) { el.textContent = text; });
    $$('[data-out-input="' + name + '"]').forEach(function (el) { el.value = text; });
  }

  function parseDate(v) {
    if (!v) return null;
    var p = v.split("-");
    return p.length === 3 ? Date.UTC(+p[0], +p[1] - 1, +p[2]) : null;
  }

  function fmtDate(ts, withYear) {
    var d = new Date(ts);
    var m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][d.getUTCMonth()];
    return String(d.getUTCDate()).padStart(2, "0") + " " + m + (withYear ? " " + d.getUTCFullYear() : "");
  }

  function plural(n, one, many) { return n === 1 ? one : many; }

  function toPaise(v) {
    var s = String(v || "").replace(/[₹,\s]/g, "").replace(/^Rs\.?/i, "");
    if (!s) return 0;
    var n = Number(s);
    return isFinite(n) && n >= 0 ? Math.round(n * 100) : NaN;
  }

  function inr(paise) {
    if (!isFinite(paise)) return "—";
    var neg = paise < 0;
    paise = Math.abs(paise);
    var whole = String(Math.floor(paise / 100));
    var frac = String(paise % 100).padStart(2, "0");
    if (whole.length > 3) {
      var head = whole.slice(0, -3), tail = whole.slice(-3), groups = [];
      while (head.length > 2) { groups.unshift(head.slice(-2)); head = head.slice(0, -2); }
      if (head) groups.unshift(head);
      whole = groups.concat(tail).join(",");
    }
    return (neg ? "-" : "") + "₹" + whole + (frac === "00" ? "" : "." + frac);
  }

  // ------------------------------------------------------------------ hotels
  var list = $("#hotel-list");
  var tpl = $("#hotel-template");

  function renumber() {
    $$("[data-hotel]", list).forEach(function (row, i) {
      $("[data-idx]", row).textContent = String(i + 1).padStart(2, "0");
    });
  }

  $("#add-hotel").addEventListener("click", function () {
    var rows = $$("[data-hotel]", list);
    var node = tpl.content.firstElementChild.cloneNode(true);
    var last = rows[rows.length - 1];
    // Chain dates: new check-in = previous check-out (or trip start)
    var prevOut = last ? $("[data-cout]", last).value : "";
    $("[data-cin]", node).value = prevOut || $("#start_date").value || "";
    list.appendChild(node);
    renumber();
    update();
    $("[data-loc]", node).focus();
  });

  list.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-remove]");
    if (!btn) return;
    var rows = $$("[data-hotel]", list);
    var row = btn.closest("[data-hotel]");
    if (rows.length === 1) {
      $$("input", row).forEach(function (i) { i.value = ""; });
    } else {
      row.remove();
    }
    renumber();
    update();
  });

  // ------------------------------------------------------------------ main update
  function update() {
    var start = parseDate($("#start_date").value);
    var end = parseDate($("#end_date").value);
    $("#end_date").min = $("#start_date").value || "";
    var days = 0, nights = 0;
    if (start !== null && end !== null && end >= start) {
      nights = Math.round((end - start) / DAY);
      days = nights + 1;
    }
    var duration = days ? days + " " + plural(days, "Day", "Days") + " / " + nights + " " + plural(nights, "Night", "Nights") : "";
    out("duration", duration || "—");
    $("#end_date").classList.toggle("is-invalid", start !== null && end !== null && end < start);

    // guest / trip
    out("guest", $("#guest_name").value.trim() || "New guest");
    out("trip", days ? fmtDate(start) + " – " + fmtDate(end, true) + " · " + duration : "Add travel dates");
    var a = parseInt($("#adults").value || "0", 10) || 0;
    var c = parseInt($("#children").value || "0", 10) || 0;
    out("travellers", String(a).padStart(2, "0") + " " + plural(a, "Adult", "Adults") + " / " +
        String(c).padStart(2, "0") + " " + plural(c, "Child", "Children"));

    // hotels
    var total = 0, count = 0, locs = [], seen = {};
    $$("[data-hotel]", list).forEach(function (row) {
      var cin = parseDate($("[data-cin]", row).value);
      var cout = parseDate($("[data-cout]", row).value);
      $("[data-cout]", row).min = $("[data-cin]", row).value || "";
      var n = cin !== null && cout !== null && cout > cin ? Math.round((cout - cin) / DAY) : 0;
      $("[data-nights]", row).value = n ? String(n).padStart(2, "0") : "";
      $("[data-cout]", row).classList.toggle("is-invalid", cin !== null && cout !== null && cout <= cin);
      var name = row.querySelector('[name="hotel_name"]').value.trim();
      if (name || n) count++;
      total += n;
      var loc = $("[data-loc]", row).value.trim();
      if (loc && !seen[loc.toLowerCase()]) { seen[loc.toLowerCase()] = 1; locs.push(loc); }
    });
    out("stay", count ? count + " " + plural(count, "Hotel", "Hotels") + " · " + total + " " + plural(total, "Night", "Nights") : "As detailed below");
    out("hotel-nights", total ? total + " of " + (nights || "—") : "—");
    out("dest-auto", locs.length ? locs.join(" – ") : "add hotels below");
    $("#destinations").placeholder = locs.join(" – ") || "Munnar – Thekkady – Vagamon – Varkala";

    var check = $("#nights-check");
    if (!nights || !total) {
      check.className = "check check--idle";
      check.textContent = "Add travel dates and hotels to check nights";
    } else if (total === nights) {
      check.className = "check check--ok";
      check.textContent = "✓ " + total + " hotel nights match the " + duration + " trip";
    } else {
      check.className = "check check--warn";
      check.textContent = "Hotel nights (" + total + ") don’t match trip nights (" + nights + ")";
    }

    // payment
    var gst = $("#gst-yes").checked;
    $("#gst-box").hidden = !gst;
    var gstin = $("#customer_gstin").value.trim().toUpperCase();
    var gstinValid = GSTIN_RE.test(gstin);
    $("#customer_gstin").classList.toggle("is-invalid", gst && gstin.length > 0 && !gstinValid);
    var igst = gst && gstinValid && /^\d\d$/.test(COMPANY_STATE) && gstin.slice(0, 2) !== COMPANY_STATE;
    var hint = $("#gstin-hint");
    if (gst && gstin && !gstinValid) hint.textContent = "GSTIN should be 15 characters, e.g. 32ABCDE1234F1Z5.";
    else if (igst) hint.textContent = "Inter-state customer → IGST 5% will be applied.";
    else if (gst && gstinValid) hint.textContent = "Same state → CGST 2.5% + SGST 2.5%.";
    else hint.textContent = "Optional. Same state → CGST 2.5% + SGST 2.5%; other state → IGST 5%.";

    var amount = toPaise($("#package_amount").value);
    var advance = toPaise($("#advance_amount").value);
    $("#package_amount").classList.toggle("is-invalid", isNaN(amount));
    $("#advance_amount").classList.toggle("is-invalid", isNaN(advance));
    var amt = isNaN(amount) ? 0 : amount, adv = isNaN(advance) ? 0 : advance;
    var cg = 0, sg = 0, ig = 0;
    if (gst) {
      if (igst) ig = Math.round(amt * 5 / 100);
      else { cg = Math.round(amt * 2.5 / 100); sg = cg; }
    }
    var grand = amt + cg + sg + ig;
    var balance = grand - adv;
    out("amount", inr(amt));
    out("cgst", inr(cg)); out("sgst", inr(sg)); out("igst", inr(ig));
    $('[data-row="cgst"]').hidden = !(gst && !igst);
    $('[data-row="sgst"]').hidden = !(gst && !igst);
    $('[data-row="igst"]').hidden = !igst;
    out("total", inr(grand));
    out("advance", inr(adv));
    out("balance", inr(balance));
    $("#advance_amount").classList.toggle("is-invalid", isNaN(advance) || balance < 0);

    var status, cls;
    if (grand > 0 && balance <= 0) { status = "Fully Paid"; cls = "paid"; }
    else if (adv > 0) { status = "Advance Paid"; cls = "advance"; }
    else { status = "Payment Pending"; cls = "pending"; }
    var pill = $('[data-out="status"]');
    pill.textContent = status;
    pill.className = "pill pill--" + cls;
  }

  form.addEventListener("input", update);
  form.addEventListener("change", update);
  $("#customer_gstin").addEventListener("blur", function () { this.value = this.value.toUpperCase().replace(/\s+/g, ""); update(); });

  // When the trip start is set and the first hotel has no check-in yet, pre-fill it.
  $("#start_date").addEventListener("change", function () {
    var first = $("[data-hotel] [data-cin]", list);
    if (first && !first.value) first.value = this.value;
    update();
  });

  // Warn before leaving with unsaved edits
  var dirty = false;
  form.addEventListener("input", function () { dirty = true; });
  form.addEventListener("submit", function () { dirty = false; });
  window.addEventListener("beforeunload", function (e) { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

  update();
})();
