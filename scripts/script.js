let lastLikesCheese = null;
let lastThinkingAboutHats = null;
let requestInFlight = false;

function formatNumber(value) {
    if (value === null || value === undefined || value === "") {
        return "N/A";
    }
    const num = Number(value);
    return Number.isFinite(num) ? num.toFixed(2) : String(value);
}

function setStatus(message, isError = false) {
    const status = document.getElementById("status");
    if (!status) {
        return;
    }
    status.textContent = message;
    status.classList.toggle("error", isError);
}

function setFormBusy(busy) {
    requestInFlight = busy;
    const form = document.getElementById("zip-form");
    const button = form ? form.querySelector("button[type='submit']") : null;
    const input = document.getElementById("zip-input");
    if (button) {
        button.disabled = busy;
    }
    if (input) {
        input.disabled = busy;
    }
}

function resetHats() {
    lastThinkingAboutHats = null;
    const button = document.getElementById("hat-button");
    const verdict = document.getElementById("hat-verdict");
    if (button) button.classList.remove("is-hidden");
    if (verdict) {
        verdict.classList.add("is-hidden");
        verdict.textContent = "";
    }
}

function revealHats() {
    console.log(`lastThinkingAboutHats: ${lastThinkingAboutHats}`)
    if (lastThinkingAboutHats === null) return;

    const notWord = lastThinkingAboutHats ? "" : "not ";
    document.getElementById("hat-verdict").textContent =
        `The user is ${notWord}thinking about hats.`;
    document.getElementById("hat-button").classList.add("is-hidden");
    document.getElementById("hat-verdict").classList.remove("is-hidden");
}

function resetCheese() {
    lastLikesCheese = null;
    const egg = document.getElementById("cheese-egg");
    const button = document.getElementById("cheese-button");
    const verdict = document.getElementById("cheese-verdict");
    if (!egg) {
        return;
    }
    egg.classList.remove("is-visible");
    if (button) {
        button.classList.remove("is-hidden");
    }
    if (verdict) {
        verdict.classList.add("is-hidden");
        verdict.textContent = "";
    }
}

function revealCheese() {
    console.log("revealCheese", lastLikesCheese);

    if (lastLikesCheese === null) {
        return;
    }
    const button = document.getElementById("cheese-button");
    const verdict = document.getElementById("cheese-verdict");
    const notWord = lastLikesCheese ? "" : "not ";
    verdict.textContent = `The user does ${notWord}like cheese.`;
    button.classList.add("is-hidden");
    verdict.classList.remove("is-hidden");
}

async function predictZip(zip) {
    const tbody = document.getElementById("forecast-table-body");
    tbody.innerHTML = "";
    resetCheese();
    resetHats();
    setStatus("Loading…");
    setFormBusy(true);

    try {
        const response = await fetch("/api/predict/" + encodeURIComponent(zip));
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Request failed (${response.status})`);
        }

        window.lastPredict = data;

        const loc = data.location;
        setStatus(
            `${loc.city}, ${loc.state} ${loc.zip} — ${data.historical_days} historical days — ${data.elapsed_ms} ms`
        );

        if (!data.forecast || data.forecast.length === 0) {
            tbody.innerHTML = "<tr><td colspan='5'>No forecast data</td></tr>";
            return;
        }

        for (const row of data.forecast) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${row.date}</td>
                <td>${formatNumber(row.temp_max)}</td>
                <td>${formatNumber(row.temp_min)}</td>
                <td>${formatNumber(row.forecast_precipitation)}</td>
                <td>${formatNumber(row.predicted_precipitation)}</td>
            `;
            tbody.appendChild(tr);
        }

        console.log(`data.diagnostics.user_likes_cheese: ${data.diagnostics.user_likes_cheese}`)
        lastLikesCheese = Boolean(data.diagnostics.user_likes_cheese);

        console.log(`data.diagnostics.user_thinking_about_hats: ${data.diagnostics.user_thinking_about_hats}`)
        lastThinkingAboutHats = Boolean(data.diagnostics.user_thinking_about_hats);

        const cheeseEgg = document.getElementById("cheese-egg");
        if (cheeseEgg) {
            cheeseEgg.classList.add("is-visible");
        }

        const hatEgg = document.getElementById("hat-egg");
        if (hatEgg) {
            hatEgg.classList.add("is-visible");
        }
    } finally {
        setFormBusy(false);
    }
}

function main() {
    const form = document.getElementById("zip-form");
    const input = document.getElementById("zip-input");
    const cheeseButton = document.getElementById("cheese-button");
    const hatButton = document.getElementById("hat-button");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (requestInFlight) {
            return;
        }
        const zip = input.value.trim();
        if (!/^\d{5}$/.test(zip)) {
            setStatus("Enter a 5-digit US ZIP code.", true);
            return;
        }
        try {
            await predictZip(zip);
        } catch (error) {
            console.error(error);
            setStatus(error.message, true);
        }
    });

    if (cheeseButton) {
        cheeseButton.addEventListener("click", revealCheese);
    }

    if (hatButton) {
        hatButton.addEventListener("click", revealHats);
    }
}

main();
