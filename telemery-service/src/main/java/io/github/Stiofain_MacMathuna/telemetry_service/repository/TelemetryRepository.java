package io.github.Stiofain_MacMathuna.telemetry_service.repository;

import io.github.Stiofain_MacMathuna.telemetry_service.model.TelemetryEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TelemetryRepository extends JpaRepository<TelemetryEvent, Long> {
    List<TelemetryEvent> findBySensorId(String sensorId);
}

