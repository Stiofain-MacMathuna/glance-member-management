package io.github.Stiofain_MacMathuna.telemetry_service;

import io.github.Stiofain_MacMathuna.telemetry_service.repository.TelemetryRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;

@Service
public class MaintenanceService {

    @Autowired
    private TelemetryRepository repository;

    // Run every 60 seconds (60000ms)
    @Scheduled(fixedRate = 60000)
    public void autoPrune() {
        // Keep only the last 10 minutes of data for the demo
        LocalDateTime cutoff = LocalDateTime.now().minusMinutes(10);
        try {
            repository.deleteOldData(cutoff);
            System.out.println("[SYSTEM-MAINTENANCE] Cleanup successful. Removed data older than: " + cutoff);
        } catch (Exception e) {
            System.err.println("[SYSTEM-MAINTENANCE] Cleanup failed: " + e.getMessage());
        }
    }
}
