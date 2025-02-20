document.addEventListener("DOMContentLoaded", function () {
    const minuteIdElement = document.querySelector("#minute-id");

    if (!minuteIdElement || !minuteIdElement.value) {
        console.error("Error: Minute ID element not found or has no value!");
        return;
    }

    const minuteId = minuteIdElement.value;
    const progressContainer = document.querySelector("#approval-chain-progress");

    console.log(`✅ Minute ID found: ${minuteId}`);

    /**
     * Fetch real-time approval progress and update UI.
     */
    async function fetchApprovalProgress() {
        try {
            console.log(`🔄 Fetching approval progress for Minute ID: ${minuteId}`);
            const response = await fetch(`/minutes/api/approval_status/${minuteId}/`);

            if (!response.ok) {
                throw new Error(`Failed to fetch approval status: ${response.status}`);
            }

            const data = await response.json();
            console.log("✅ Approval Status Data:", data);

            if (!data.approval_chain || data.approval_chain.length === 0) {
                progressContainer.innerHTML = `<p class="text-center text-danger">No approval data available.</p>`;
                return;
            }

            // ✅ FIX: Sort the approval chain based on 'order' before rendering
            data.approval_chain.sort((a, b) => a.order - b.order);

            updateApprovalChainTimeline(data.approval_chain);
        } catch (error) {
            console.error("🚨 Error fetching approval status:", error);
            progressContainer.innerHTML = `<p class="text-center text-danger">Failed to load approval chain progress.</p>`;
        }
    }

    /**
     * Update the approval chain timeline visualization (No Remarks).
     */
    function updateApprovalChainTimeline(approversStatus) {
        progressContainer.innerHTML = ""; // Clear previous content

        let progressHTML = `<div class="chain-timeline">`;

        approversStatus.forEach((approver, index) => {
            let statusBadge = getStatusBadge(approver.status);

            progressHTML += `
                <div class="chain-item">
                    <div class="approver-name">${approver.approver}</div>
                    <div class="status-badge">${statusBadge}</div>
                    <div class="action-time">${approver.action_time || "Pending"}</div>
                </div>`;

            // Add arrow between steps (except last item)
            if (index < approversStatus.length - 1) {
                progressHTML += `<div class="chain-arrow">→</div>`;
            }
        });

        progressHTML += `</div>`;
        progressContainer.innerHTML = progressHTML;
    }

    /**
     * Get Bootstrap badge class for different statuses.
     */
    function getStatusBadge(status) {
        switch (status.toLowerCase()) {
            case "approved":
                return `<span class="badge bg-success">Approved</span>`;
            case "rejected":
                return `<span class="badge bg-danger">Rejected</span>`;
            case "pending":
                return `<span class="badge bg-warning text-dark">Pending</span>`;
            case "marked":
                return `<span class="badge bg-info">Marked-To</span>`;
            case "returned":
                return `<span class="badge bg-secondary">Returned</span>`;
            default:
                return `<span class="badge bg-secondary">Unknown</span>`;
        }
    }

    setInterval(fetchApprovalProgress, 10000);
    fetchApprovalProgress();
});
