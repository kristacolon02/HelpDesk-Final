/*
 * 12/11/2026 - Krista Colon: logica de INCIDENTES (incidents.html), examen final, ficha 07. Sigue las reglas del
 * cliente del 22/10/2026: los datos de la API entran al DOM con textContent (nunca como HTML) y cada peticion
 * pasa por request() de api.js, que agrega el token y traduce los errores al sobre comun de la API.
 */

import { request, userMessage } from "../api.js";
import { STATUS_LABELS, formatDateTime, label } from "../format.js";
import { bootPage } from "../layout.js";
import { badge, clearAlert, clearFieldErrors, el, loadingIndicator, setBusy, setFlash, showAlert, showFieldErrors, toast } from "../ui.js";

const alertRegion = document.getElementById("alert-region");
const createForm = document.getElementById("create-form");
const createButton = document.getElementById("create-button");
const listContainer = document.getElementById("incident-list");
const detailContainer = document.getElementById("incident-detail");

// 12/11/2026 - Krista Colon: solo estos roles crean incidentes y vinculan tickets (igual que IncidentService).
const MANAGER_ROLES = ["supervisor", "administrator"];

// 12/11/2026 - Krista Colon: mensajes en espanol para los errores propios del modulo.
const INCIDENT_MESSAGES = {
  ticket_already_linked: "Ese ticket ya pertenece a otro incidente: un ticket solo puede estar en uno.",
  ticket_not_eligible: "Solo se pueden vincular tickets abiertos o en proceso.",
  incident_not_open: "El incidente ya está resuelto: no admite más tickets.",
  incident_not_found: "El incidente no existe.",
  ticket_not_found: "No existe un ticket con ese número.",
  permission_denied: "Solo un supervisor o un administrador puede hacer esta operación.",
};

const incidentApi = {
  list: async () => (await request("GET", "/incidents")).data,
  get: async (id) => (await request("GET", `/incidents/${id}`)).data,
  create: async (payload) => (await request("POST", "/incidents", { body: payload })).data,
  link: async (id, ticketId) => (await request("POST", `/incidents/${id}/tickets`, { body: { ticket_id: ticketId } })).data,
};

let currentUser = null;

function messageFor(error) {
  return INCIDENT_MESSAGES[error?.code] ?? userMessage(error);
}

function isManager() {
  return Boolean(currentUser) && MANAGER_ROLES.includes(currentUser.role);
}

function selectedId() {
  const id = Number(new URLSearchParams(window.location.search).get("id"));
  return Number.isInteger(id) && id > 0 ? id : null;
}

function statusBadge(status) {
  return status === "open" ? badge("Abierto", "text-bg-warning") : badge("Resuelto", "text-bg-success");
}

// --- lista ------------------------------------------------------------------

function renderList(items) {
  if (items.length === 0) {
    listContainer.replaceChildren(el("p", { className: "text-body-secondary", text: "Todavía no hay incidentes." }));
    return;
  }
  const current = selectedId();
  listContainer.replaceChildren(
    el(
      "div",
      { className: "list-group" },
      ...items.map((incident) =>
        el(
          "a",
          {
            className: `list-group-item list-group-item-action${incident.id === current ? " active" : ""}`,
            attrs: { href: `incidents.html?id=${Number(incident.id)}`, "aria-current": incident.id === current ? "true" : false },
          },
          el(
            "div",
            { className: "d-flex justify-content-between gap-2" },
            el("strong", { text: `#${incident.id} ${incident.title}` }),
            statusBadge(incident.status),
          ),
          el("small", { text: `${incident.ticket_count} ticket(s) · ${formatDateTime(incident.created_at)}` }),
        ),
      ),
    ),
  );
}

async function loadList() {
  listContainer.replaceChildren(loadingIndicator("Cargando incidentes…"));
  try {
    renderList(await incidentApi.list());
  } catch (error) {
    listContainer.replaceChildren();
    showAlert(alertRegion, messageFor(error));
  }
}

// --- detalle ----------------------------------------------------------------

function linkForm(incident) {
  if (!isManager() || incident.status !== "open") {
    return null;
  }
  const input = el("input", {
    className: "form-control",
    attrs: { id: "ticket-number", name: "ticket_id", type: "number", min: "1", required: true, inputmode: "numeric" },
  });
  const button = el("button", { className: "btn btn-primary", text: "Vincular", attrs: { type: "submit" } });
  const form = el(
    "form",
    { className: "mt-3", attrs: { novalidate: true } },
    el("label", { className: "form-label", text: "Número de ticket a vincular", attrs: { for: "ticket-number" } }),
    el("div", { className: "input-group" }, input, button),
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert(alertRegion);
    const ticketId = Number(input.value);
    if (!Number.isInteger(ticketId) || ticketId < 1) {
      showAlert(alertRegion, "Escribe un número de ticket válido.");
      input.focus();
      return;
    }
    setBusy(button, true, "Vinculando…");
    try {
      renderDetail(await incidentApi.link(incident.id, ticketId));
      toast(`Ticket #${ticketId} vinculado al incidente #${incident.id}.`);
      await loadList();
    } catch (error) {
      showAlert(alertRegion, messageFor(error));
      setBusy(button, false);
    }
  });
  return form;
}

function renderDetail(incident) {
  const tickets =
    incident.tickets.length === 0
      ? el("p", { className: "text-body-secondary mb-0", text: "Este incidente todavía no tiene tickets vinculados." })
      : el(
          "ul",
          { className: "list-group" },
          ...incident.tickets.map((ticket) =>
            el(
              "li",
              { className: "list-group-item d-flex justify-content-between gap-2" },
              el("a", { text: `#${ticket.id} ${ticket.title}`, attrs: { href: `ticket.html?id=${Number(ticket.id)}` } }),
              el("span", { className: "small text-nowrap", text: label(STATUS_LABELS, ticket.status) }),
            ),
          ),
        );

  // replaceChildren() escribiria "null" como texto: por eso quito las partes vacias antes.
  const parts = [
    el("div", { className: "d-flex justify-content-between gap-2" }, el("h3", { className: "h5 mb-1", text: `#${incident.id} ${incident.title}` }), statusBadge(incident.status)),
    el("p", { className: "small text-body-secondary", text: `Creado el ${formatDateTime(incident.created_at)}` }),
    incident.description ? el("p", { text: incident.description }) : null,
    el("h4", { className: "h6", text: `Tickets vinculados (${incident.tickets.length})` }),
    tickets,
    linkForm(incident),
  ].filter((part) => part !== null);
  detailContainer.replaceChildren(...parts);
}

async function loadDetail() {
  const id = selectedId();
  if (id === null) {
    return;
  }
  detailContainer.replaceChildren(loadingIndicator("Cargando detalle…"));
  try {
    renderDetail(await incidentApi.get(id));
  } catch (error) {
    detailContainer.replaceChildren(el("p", { className: "mb-0", text: messageFor(error) }));
  }
}

// --- crear ------------------------------------------------------------------

async function createIncident(event) {
  event.preventDefault();
  clearAlert(alertRegion);
  clearFieldErrors(createForm);
  const title = createForm.elements.title.value.trim();
  if (title.length < 3) {
    showFieldErrors(createForm, { title: "El título debe tener al menos 3 caracteres." });
    return;
  }
  setBusy(createButton, true, "Creando…");
  try {
    const incident = await incidentApi.create({ title, description: createForm.elements.description.value.trim() });
    // Navego al detalle del nuevo incidente: la URL con ?id= permite recargar y ver el mismo registro.
    setFlash(`Incidente #${incident.id} creado.`);
    window.location.assign(`incidents.html?id=${Number(incident.id)}`);
  } catch (error) {
    showAlert(alertRegion, messageFor(error));
    setBusy(createButton, false);
  }
}

currentUser = await bootPage("incidents");
if (currentUser) {
  if (isManager()) {
    createForm.classList.remove("d-none");
    createForm.addEventListener("submit", createIncident);
  }
  await Promise.all([loadList(), loadDetail()]);
}
