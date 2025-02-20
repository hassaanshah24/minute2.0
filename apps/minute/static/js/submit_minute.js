// submit_minute.js

document.addEventListener("DOMContentLoaded", function () {
    const minuteForm = document.querySelector("#minute-form");
    const submitButton = document.querySelector("#submit-button");
    const errorContainer = document.querySelector("#error-messages");

    if (!minuteForm || !submitButton) {
        console.error("Minute form or submit button not found.");
        return;
    }

    submitButton.addEventListener("click", async function (event) {
        event.preventDefault();
        clearErrors();

        // Validate form fields
        const title = document.querySelector("#title").value.trim();
        const description = document.querySelector("#description").value.trim();
        const approvalChain = document.querySelector("#approval_chain").value;

        if (!title || !description || !approvalChain) {
            displayError("All fields (Title, Description, Approval Chain) are required.");
            return;
        }

        // Confirm submission
        if (!confirm("Are you sure you want to submit this minute?")) {
            return;
        }

        // Gather form data
        const formData = new FormData(minuteForm);

        try {
            // Disable submit button to prevent multiple clicks
            toggleSubmitButton(true);

            const response = await fetch(minuteForm.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
                },
            });

            if (response.ok) {
                const data = await response.json();
                showSuccess("Minute submitted successfully!", data.minute.id);
            } else {
                const errorData = await response.json();
                displayError(errorData.error || "An unexpected error occurred during submission.");
            }
        } catch (error) {
            console.error("Error submitting the minute:", error);
            displayError("A network error occurred. Please try again.");
        } finally {
            toggleSubmitButton(false);
        }
    });

    /**
     * Display error messages in the error container or as an alert.
     * @param {string} message - The error message to display.
     */
    function displayError(message) {
        if (errorContainer) {
            errorContainer.innerHTML = `<div class="alert alert-danger">${message}</div>`;
            errorContainer.scrollIntoView({ behavior: "smooth" });
        } else {
            alert(message);
        }
    }

    /**
     * Clear all errors from the error container.
     */
    function clearErrors() {
        if (errorContainer) {
            errorContainer.innerHTML = "";
        }
    }

    /**
     * Toggle the submit button state between enabled and disabled.
     * @param {boolean} isSubmitting - Whether the form is currently being submitted.
     */
    function toggleSubmitButton(isSubmitting) {
        submitButton.disabled = isSubmitting;
        submitButton.textContent = isSubmitting ? "Submitting..." : "Submit";
    }

    /**
     * Redirect to success page and show a success message.
     * @param {string} message - The success message to display.
     * @param {number} minuteId - The ID of the submitted minute.
     */
    function showSuccess(message, minuteId) {
        alert(message);
        window.location.href = `/minute/submit_success/${minuteId}/`;
    }
});
