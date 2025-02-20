document.addEventListener("DOMContentLoaded", function () {
    const minuteId = document.getElementById("minute-id") ? document.getElementById("minute-id").value : null;
    const approvalChainContainer = document.getElementById("approval-chain");

    function fetchApprovalStatus() {
        if (!minuteId) return;

        fetch(`/minute/api/approval_status/${minuteId}/`)
            .then(response => response.json())
            .then(data => {
                approvalChainContainer.innerHTML = "";

                let approvalTimeline = `<ul class="timeline">`;
                data.approval_chain.forEach(approver => {
                    let statusBadge = "";
                    let iconClass = "";

                    if (approver.status === "Approved") {
                        statusBadge = `<span class="badge bg-success">Approved</span>`;
                        iconClass = "fas fa-check-circle text-success";
                    } else if (approver.status === "Pending") {
                        statusBadge = `<span class="badge bg-warning">Pending</span>`;
                        iconClass = "fas fa-hourglass-half text-warning";
                    } else if (approver.status === "Rejected") {
                        statusBadge = `<span class="badge bg-danger">Rejected</span>`;
                        iconClass = "fas fa-times-circle text-danger";
                    } else if (approver.status === "Marked") {
                        statusBadge = `<span class="badge bg-info">Marked-To</span>`;
                        iconClass = "fas fa-exchange-alt text-info";
                    }

                    approvalTimeline += `
                        <li class="timeline-item">
                            <i class="${iconClass}"></i>
                            <div class="timeline-content">
                                <span class="fw-bold">${approver.approver}</span>
                                ${statusBadge}
                                <p>${approver.remarks || "No remarks provided"}</p>
                                <small class="text-muted">${approver.action_time}</small>
                            </div>
                        </li>`;
                });
                approvalTimeline += `</ul>`;

                approvalChainContainer.innerHTML = approvalTimeline;
            })
            .catch(error => console.error("Error fetching approval status:", error));
    }

    // Fetch approval status every 5 seconds
    setInterval(fetchApprovalStatus, 5000);
    fetchApprovalStatus(); // Initial fetch on page load
});
