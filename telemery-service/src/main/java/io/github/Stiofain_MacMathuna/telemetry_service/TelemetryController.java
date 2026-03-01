package io.github.Stiofain_MacMathuna.telemetry_service;

import io.github.Stiofain_MacMathuna.telemetry_service.model.TelemetryEvent;
import io.github.Stiofain_MacMathuna.telemetry_service.repository.TelemetryRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@RestController
@RequestMapping("api/v1/telemetry")
public class TelemetryController {

    @Autowired
    private TelemetryRepository repository;

    // Multithreading: Dedicated pool for processing sensor data
    private final ExecutorService executor = Executors.newFixedThreadPool(10);

    @PostMapping("/ingest")
    public String ingestData(@RequestBody TelemetryEvent event) {
        // Set a timestamp if one wasn't provided in the JSON
        if (event.getTimestamp() == null) {
            event.setTimestamp(LocalDateTime.now());
        }

        executor.submit(() -> {
            // 1. Simulate complex analysis (CERN Post-Mortem style)
            System.out.println("[POST-MORTEM] Analyzing " + event.getEventType() +
                    " from Sensor: " + event.getSensorId());

            try {
                Thread.sleep(1500); // Simulating heavy analysis
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

            // 2. Persist the result to PostgreSQL
            repository.save(event);

            System.out.println("[ARCHIVE] Event from " + event.getSensorId() + " successfully persisted to DB.");
        });

        return "CERN Telemetry Ingested: Event queued for analysis and persistence.";
    }

    @GetMapping("/history")
    public List<TelemetryEvent> getHistory() {
        // Returns all events, newest first
        return repository.findAll(org.springframework.data.domain.Sort.by(
                org.springframework.data.domain.Sort.Direction.DESC, "timestamp"));
    }

    @GetMapping("/sensor/{sensorId}")
    public List<TelemetryEvent> getBySensor(@PathVariable String sensorId) {
        return repository.findBySensorId(sensorId);
    }

    @DeleteMapping("/history")
    public ResponseEntity<String> clearHistory() {
        repository.deleteAll();
        return ResponseEntity.ok("Post-Mortem buffer cleared. System ready for new fill.");
    }
}