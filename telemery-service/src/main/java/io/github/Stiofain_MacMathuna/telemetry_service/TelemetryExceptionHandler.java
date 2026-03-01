package io.github.Stiofain_MacMathuna.telemetry_service;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

@ControllerAdvice
public class TelemetryExceptionHandler {

    @ExceptionHandler(Exception.class)
    public ResponseEntity<String> handleGeneralError(Exception e) {
        System.err.println("[CRITICAL ERROR] Pipeline Interrupted: " + e.getMessage());
        return ResponseEntity.internalServerError().body("Telemetry Pipeline Error: Check logs.");
    }
}