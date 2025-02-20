document.addEventListener('DOMContentLoaded', function () {
    const approversField = document.getElementById('id_approvers');
    const chainVisualization = document.getElementById('chain-visualization');
    let selectedApprovers = [];

    // Utility: Render Mermaid graph
    const renderMermaidGraph = () => {
        try {
            if (selectedApprovers.length > 0) {
                const mermaidGraph = selectedApprovers
                    .map((approver, index) => `${index + 1}["${approver.text}"]`)
                    .join(' --> ');
                chainVisualization.textContent = `graph TD\n${mermaidGraph}`;
                mermaid.init(undefined, chainVisualization); // Render graph
            } else {
                chainVisualization.textContent = 'graph TD\nNoApprover[No Approvers Added]';
                mermaid.init(undefined, chainVisualization); // Render fallback graph
            }
        } catch (error) {
            console.error('Error rendering Mermaid graph:', error);
            chainVisualization.textContent = 'Error rendering the approval chain.';
        }
    };

    // Add selected approvers
    const addApprovers = () => {
        const selectedOptions = Array.from(approversField.selectedOptions);
        selectedOptions.forEach(option => {
            if (!selectedApprovers.some(approver => approver.value === option.value)) {
                selectedApprovers.push({ value: option.value, text: option.text });
            }
        });
        renderMermaidGraph();
        displayMessage('Approvers added successfully.', 'success');
    };

    // Remove selected approvers
    const removeApprovers = () => {
        const selectedOptions = Array.from(approversField.selectedOptions);
        selectedApprovers = selectedApprovers.filter(
            approver => !selectedOptions.some(option => approver.value === option.value)
        );
        renderMermaidGraph();
        displayMessage('Approvers removed successfully.', 'success');
    };

    // Serialize approvers into a hidden input field for form submission
    const serializeApprovers = (form) => {
        try {
            // Remove any existing hidden input for approvers
            const existingInput = form.querySelector('input[name="approvers"]');
            if (existingInput) {
                existingInput.remove();
            }

            // Create a new input for the serialized approvers
            const approversInput = document.createElement('input');
            approversInput.type = 'hidden';
            approversInput.name = 'approvers';
            approversInput.value = JSON.stringify(selectedApprovers);
            form.appendChild(approversInput);
        } catch (error) {
            console.error('Error serializing approvers:', error);
            displayMessage('Failed to serialize approvers.', 'error');
        }
    };

    // Display feedback message
    const displayMessage = (message, type) => {
        const messageContainer = document.getElementById('message-container');
        if (messageContainer) {
            messageContainer.textContent = message;
            messageContainer.className = `alert alert-${type === 'success' ? 'success' : 'danger'}`;
        }
    };

    // Attach event listeners
    document.getElementById('add-approver')?.addEventListener('click', addApprovers);
    document.getElementById('remove-approver')?.addEventListener('click', removeApprovers);

    // Add form submission listener
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function (event) {
            serializeApprovers(form);
        });
    }

    // Initialize Mermaid.js
    mermaid.initialize({ startOnLoad: false });

    // Render initial visualization
    renderMermaidGraph();
});
