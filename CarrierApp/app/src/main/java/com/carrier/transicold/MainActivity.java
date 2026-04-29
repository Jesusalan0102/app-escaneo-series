package com.carrier.transicold;

import android.annotation.SuppressLint;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Button;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout errorLayout;
    private String appUrl;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        appUrl = getIntent().getStringExtra("url");
        if (appUrl == null) appUrl = SplashActivity.APP_URL;

        webView    = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);
        errorLayout = findViewById(R.id.errorLayout);
        Button btnRetry = findViewById(R.id.btnRetry);

        btnRetry.setOnClickListener(v -> loadApp());

        setupWebView();

        if (isConnected()) {
            loadApp();
        } else {
            showError("Sin conexión a internet.\nConéctate e intenta de nuevo.");
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = webView.getSettings();

        // JavaScript habilitado (necesario para Streamlit)
        settings.setJavaScriptEnabled(true);

        // Evita que el WebView recargue al hacer scroll
        settings.setDomStorageEnabled(true);
        
        

        // WebSocket y recursos multimedia
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        // Zoom desactivado — se ve como app nativa
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        // Cache: carga siempre desde red (evita contenido desactualizado)
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);

        // User agent — se identifica como app móvil
        settings.setUserAgentString(
            "CarrierTransicold/1.0 Android/" + android.os.Build.VERSION.RELEASE
        );

        // Viewport responsive
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);

        webView.setScrollBarStyle(View.SCROLLBARS_INSIDE_OVERLAY);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);  // ← Sin rebote al scroll

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                if (newProgress == 100) {
                    progressBar.setVisibility(View.GONE);
                } else {
                    progressBar.setVisibility(View.VISIBLE);
                }
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                // Mantener todas las URLs dentro del WebView (no abrir navegador)
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                errorLayout.setVisibility(View.GONE);
                webView.setVisibility(View.VISIBLE);

                // Inyectar CSS para ocultar branding de Streamlit desde el WebView
                String css =
                    "header[data-testid='stHeader']{display:none!important;}" +
                    "footer{display:none!important;}" +
                    "#MainMenu{display:none!important;}" +
                    ".stDeployButton{display:none!important;}" +
                    "[data-testid='stToolbar']{display:none!important;}" +
                    "[data-testid='stStatusWidget']{display:none!important;}" +
                    ".block-container{padding-top:1rem!important;}";

                String cssJs = "javascript:(function(){" +
                    "var s=document.createElement('style');" +
                    "s.innerHTML='" + css + "';" +
                    "document.head.appendChild(s);" +
                    "})()";

                view.loadUrl(cssJs);

                // Refresh automático cada 30s — se pausa si el usuario está scrolleando
                // Espera 4 segundos sin scroll antes de refrescar
                String refreshJs = "javascript:(function(){" +
                    "if(window._carrierRefreshActive) return;" +
                    "window._carrierRefreshActive = true;" +
                    "var _scrolling=false,_scrollTimer=null,_refreshTimer=null;" +
                    "function doRefresh(){" +
                    "  if(!_scrolling){window.location.reload();}" +
                    "  else{scheduleRefresh();}" +
                    "}" +
                    "function scheduleRefresh(){" +
                    "  clearTimeout(_refreshTimer);" +
                    "  _refreshTimer=setTimeout(doRefresh,30000);" +
                    "}" +
                    "window.addEventListener('scroll',function(){" +
                    "  _scrolling=true;" +
                    "  clearTimeout(_refreshTimer);" +
                    "  clearTimeout(_scrollTimer);" +
                    "  _scrollTimer=setTimeout(function(){" +
                    "    _scrolling=false;" +
                    "    scheduleRefresh();" +
                    "  },4000);" +
                    "},{passive:true});" +
                    "scheduleRefresh();" +
                    "})()";

                view.loadUrl(refreshJs);
            }

            @Override
            public void onReceivedError(WebView view, int errorCode,
                                        String description, String failingUrl) {
                showError("No se pudo cargar la aplicación.\n\nCódigo: " + errorCode);
            }
        });
    }

    private void loadApp() {
        errorLayout.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
        progressBar.setVisibility(View.VISIBLE);
        webView.loadUrl(appUrl);
    }

    private void showError(String message) {
        webView.setVisibility(View.GONE);
        progressBar.setVisibility(View.GONE);
        errorLayout.setVisibility(View.VISIBLE);
        TextView tvError = findViewById(R.id.tvError);
        tvError.setText(message);
    }

    private boolean isConnected() {
        ConnectivityManager cm = (ConnectivityManager)
            getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo info = cm.getActiveNetworkInfo();
        return info != null && info.isConnected();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
    }
}
