package io.github.Stiofain_MacMathuna.telemetry_service;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class LhcEvent {
    private String sensorId;
    private String eventType;
    private double value;
    private LocalDateTime timestamp = LocalDateTime.now();
}