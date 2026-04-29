package com.carrier.transicold;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import androidx.appcompat.app.AppCompatActivity;

public class SplashActivity extends AppCompatActivity {

    // ⬇️ CAMBIA ESTA URL POR LA URL DE TU APP EN CLEVER CLOUD
    public static final String APP_URL = "https://app-69f175bc-dc87-401a-aad1-d112712f8b6d.cleverapps.io";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);

        // Mostrar splash 2 segundos y luego abrir la app
        new Handler().postDelayed(() -> {
            Intent intent = new Intent(SplashActivity.this, MainActivity.class);
            intent.putExtra("url", APP_URL);
            startActivity(intent);
        }, 2000);
    }
}
