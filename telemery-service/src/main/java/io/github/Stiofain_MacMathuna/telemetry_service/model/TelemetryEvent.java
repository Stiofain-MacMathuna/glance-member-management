package io.github.Stiofain_MacMathuna.telemetry_service.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import jakarta.validation.constraints.Min;

@Entity
@Table(name = "telemetry_events")
@Data
public class    TelemetryEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String sensorId;
    private String eventType;
    private Integer fillNumber;
    private String accelerator;

    private LocalDateTime timestamp;

    @Min(value = 0, message = "Beam intensity cannot be negative")
    private Double value;
}