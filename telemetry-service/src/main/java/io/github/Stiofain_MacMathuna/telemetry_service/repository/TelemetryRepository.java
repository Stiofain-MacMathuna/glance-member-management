package io.github.Stiofain_MacMathuna.telemetry_service.repository;

import io.github.Stiofain_MacMathuna.telemetry_service.model.TelemetryEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface TelemetryRepository extends JpaRepository<TelemetryEvent, Long> {
    
    List<TelemetryEvent> findBySensorId(String sensorId);

    List<TelemetryEvent> findTop100ByOrderByTimestampDesc();

    @Transactional
    @Modifying
    @Query("DELETE FROM TelemetryEvent t WHERE t.timestamp < :cutoff")
    void deleteOldData(@Param("cutoff") LocalDateTime cutoff);
}
