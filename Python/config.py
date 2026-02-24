TECH_OWNER_KNOWLEDGE = {
    "INFRA": {
        "full_name": "Divisi Infrastruktur",
        "description": "Mengelola infrastruktur dan layanan IT perusahaan",
        "scope": "Jaringan, server & cloud, keamanan sistem, maintenance perangkat, backup & monitoring sistem",
        "used_operation": ["CreateVolume-Gp3", "CreateVolume", "RunInstances", "EBS:IO-Write", "PublicIP-In", "GET", "GlacierInstantRetrievalStorage", "CreateVolume-Sc1", "InterZone-In", "Hourly", "EBS:IO-Read", "ReadCostAllocation", "PublicIP-Out", "GetObject", "CreateVolume-St1", "HeadBucket", "LoadBalancing:Network", "StandardStorage", "POST", "OPTIONS", "InterZone-Out", "DeepArchiveS3ObjectOverhead", "ObjectTagCount", "PutObject", "OneZoneIASizeOverhead", "OneZoneIAStorage", "DELETE", "ReadACL", "HEAD", "PUT", "GlacierStorage", "DeepArchiveStagingStorage", "GlacierObjectOverhead", "GlacierS3ObjectOverhead", "IntelligentTieringAIAStorage", "HeadObject", "DeleteObject", "PreflightRequest", "CreateSnapshot", "ReadLocation", "ReadBucketPublicAccessBlock", "ReadBucketPolicyStatus", "ReadBucketPolicy", "UploadPart", "ListBucket", "InitiateMultipartUpload", "CompleteMultipartUpload", "ReadLogProps", "ReadVersioningProps", "ReadAccelerate", "ReadBucketOwnershipControls", "ReadBucketIntelligentTiering", "ReadBucketServerSideEncryption", "ReadRequestPaymentProps", "ReadNotificationProps", "WriteCostAllocation", "ReadBucketCors", "ReadBucketLifecycle", "ReadBucketInventory", "ReadBucketAnalytics", "ReadObjectTagging", "ReadBucketReplication"],
        "products_handled": ["Storage", "Data Transfer", "Compute Instance", "System Operation", "Request", "API Request", "Load Balancer-Network", "Storage Snapshot"],
        "projects_handled": ["SIMPKB", "SIMPATIKA", "PerlindunganPTK", "SekolahPenggerak", "BELMAWA", "DiklatDIKMENDIKSUS", "infra", "PPG", "Inkubasi", "GBGTKPAUDDB", "GPO", "PPGMUTU", "P2GTKMP", "TAMASKA", "DIKLATKSPS", "GuruPenggerak", "BACKUP", "CDN", "praktik-baik", "PBS", "PPGPRAJAB", "dio", "LMSERKAM", "UKKJ", "SMARTVILLAGE", "GPK", "PPDB-Online", "PSP-DIKLAT-IKM-PS", "MASOOK", "GBGTKPAUD", "KEMENSOS", "SmartCityNavigator", "PPGMUTUPPKS", "PPB", "MONEV", "UKKT", "eparkir", "GBP3K", "PERSONALPTK"]
    },
    "DIP": {
        "full_name": "Divisi Integrasi dan Pengembangan",
        "description": "Mengembangkan dan mengintegrasikan sistem/aplikasi perusahaan",
        "scope": "Pengembangan frontend & backend, UI/UX, integrasi API, testing, deployment, dan maintenance sistem",
        "used_operation": ["InterZone-Out", "CreateVolume", "Hourly", "RunInstances", "EBS:IO-Write", "InterZone-In", "RunInstances:SV003", "EBS:IO-Read", "RunInstances:SV002", "HeadBucket", "PublicIP-Out", "CreateVolume-Gp3", "PublicIP-In", "ReadCostAllocation", "StandardStorage", "ReadACL", "ReadBucketPolicyStatus", "ReadLocation", "ReadBucketPolicy", "ReadBucketPublicAccessBlock", "ListBucket", "CreateSnapshot", "T4GCPUCredits", "ReadVersioningProps", "ReadBucketOwnershipControls", "GetObject"],
        "products_handled": ["Data Transfer", "Storage", "Compute Instance", "System Operation", "API Request", "Storage Snapshot", "CPU Credits"],
        "projects_handled": ["PerlindunganPTK", "CDN", "SekolahPenggerak", "PPG", "SIMPKB", "smkpk-rekognisi", "DIKLATKSPS", "DiklatDIKMENDIKSUS", "PPGPRAJAB", "Inkubasi", "GuruPenggerak", "PPGMUTU", "P2GTKMP", "UKKJ", "GBGTKPAUDDB", "praktik-baik", "SIMPATIKA", "PERSONALPTK"]
    },
    "DLA": {
        "full_name": "Divisi Layanan Data dan Analitik",
        "description": "Mengelola data dan menghasilkan insight berbasis data",
        "scope": "Pemrosesan data, dashboard & reporting, analisis bisnis, AI/Machine Learning, data quality",
        "used_operation": ["CreateDBInstance:0018", "InterZone-In", "CreateDBInstance:0016", "InterZone-Out", "RunInstances", "Hourly", "CreateVolume", "CreateVolume-Gp3", "EBS:IO-Write", "EBS:IO-Read", "CreateDBInstance", "CreateSnapshot"],
        "products_handled": ["Data Transfer", "Database Storage", "Database Instance", "Compute Instance", "Storage", "System Operation", "Storage Snapshot"],
        "projects_handled": ["PPG", "GBGTKPAUDDB", "SIMPKB", "SIMPATIKA", "PPGPRAJAB", "Inkubasi", "GuruPenggerak", "SekolahPenggerak", "P2GTKMP", "infra"]
    },
    "DPP": {
        "full_name": "Divisi Pengembangan dan Produk",
        "description": "Mengembangkan dan mengintegrasikan sistem/aplikasi perusahaan",
        "scope": "Pengembangan frontend & backend, UI/UX, integrasi API, testing, deployment, dan maintenance sistem",
        "used_operation": ["ReadCostAllocation", "CreateVolume", "ApiGatewayRequest", "HeadBucket", "StandardStorage", "EBS:IO-Read", "RunInstances", "Invoke", "InterZone-In", "Hourly", "PutLogEvents", "EBS:IO-Write", "InterZone-Out", "Shutdown", "HourlyStorageMetering", "ReadBucketPublicAccessBlock", "ReadBucketPolicy", "ReadLocation", "ReadACL", "ReadBucketPolicyStatus"],
        "products_handled": ["Data Transfer", "Storage", "API Calls", "API Request", "System Operation", "Compute Instance", "Serverless", "Data Payload", "Storage Snapshot"],
        "projects_handled": ["SIMPKB", "DiklatDIKMENDIKSUS", "SIMPATIKA", "MASOOK", "PPG"]
    },
    "Minova": {
        "full_name": "PT Mitra Inovasi Jayantara (Vendor/Partner)",
        "description": "Perusahaan mitra TIK yang fokus pada pengembangan layanan Software as a Service (SaaS) berskala nasional untuk sektor pendidikan dan pemerintahan",
        "scope": "Pengembangan aplikasi cloud (SaaS), pengelolaan infrastruktur data storage, dan manajemen backup/snapshot (EBS) untuk proyek aplikasi eksternal.",
        "used_operation": ["CreateVolume", "EBS:IO-Read", "EBS:IO-Write", "CreateSnapshot"],
        "products_handled": ["Storage", "System Operation", "Storage Snapshot"],
        "projects_handled": ["GuruPenggerak", "UKKJ", "P2GTMP"]
    },
    "DAK": {
        "full_name": "Divisi Administrasi dan Keuangan",
        "description": "Mengelola administrasi, keuangan, dan sumber daya perusahaan",
        "scope": "Keuangan & budgeting, HR & payroll, legal & perizinan, aset & inventaris, pajak & compliance",
        "used_operation": ["RunInstances", "Hourly"],
        "products_handled": ["Compute Instance"],
        "projects_handled": ["infra"]
    }
}
